"""Sistema de media (§5, §8, §9, §14, §43).

Regras que este módulo garante:

* validação de formato por número MIME **e** por conteúdo real (Pillow
  reabre o ficheiro — não confiamos na extensão nem no header enviado);
* limite de tamanho e de dimensões;
* geração de versões otimizadas (WebP) — nunca se serve o original gigante;
* registo de autoria, proveniência e estado de moderação;
* armazenamento por checksum, para a mesma imagem não ser guardada duas vezes.
"""
from __future__ import annotations

import hashlib
import io
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.constants import (
    MEDIA_APPROVED, MEDIA_SOURCE_OFFICIAL, MEDIA_SOURCE_COMMUNITY,
    MEDIA_PENDING, MEDIA_MAIN,
)
from app.models.media import Media

# Pillow precisa disto para abrir HEIC em máquinas que o tenham compilado.
try:  # pragma: no cover - depende do build do Pillow
    import pillow_heif  # type: ignore

    pillow_heif.register_heif_opener()
    HEIC_SUPPORTED = True
except Exception:  # pragma: no cover
    HEIC_SUPPORTED = False

SUPPORTED_FORMATS = {"JPEG", "PNG", "WEBP", "HEIF"}
VARIANT_FORMAT = "webp"
VARIANT_QUALITY = 82


class MediaRejected(Exception):
    """A imagem não passou na validação. A mensagem é para o utilizador."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


@dataclass
class StoredImage:
    storage_key: str
    width: int
    height: int
    bytes: int
    checksum: str
    mime_type: str
    variants: dict[str, str]


def media_root() -> Path:
    root = Path(settings.MEDIA_ROOT)
    root.mkdir(parents=True, exist_ok=True)
    return root


def _abspath(storage_key: str) -> Path:
    """Resolve uma chave relativa dentro de MEDIA_ROOT, recusando qualquer
    tentativa de sair do diretório."""
    root = media_root().resolve()
    target = (root / storage_key).resolve()
    if not str(target).startswith(str(root)):
        raise MediaRejected("Caminho de ficheiro inválido.")
    return target


def validate(raw: bytes) -> tuple[Image.Image, str, int, int]:
    """Abre e valida. Devolve (imagem, formato, largura, altura)."""
    if not raw:
        raise MediaRejected("O ficheiro está vazio.")
    if len(raw) > settings.media_max_bytes:
        limit_mb = settings.MEDIA_MAX_UPLOAD_MB
        raise MediaRejected(
            f"A imagem tem mais de {limit_mb} MB. Reduz o tamanho e tenta de novo."
        )

    try:
        img = Image.open(io.BytesIO(raw))
        img.verify()
    except (UnidentifiedImageError, OSError, ValueError):
        raise MediaRejected(
            "Não conseguimos ler esta imagem. Usa JPG, PNG ou WEBP."
        )

    try:
        img = Image.open(io.BytesIO(raw))
        img = ImageOps.exif_transpose(img) or img
    except Exception:
        raise MediaRejected("A imagem está corrompida.")

    fmt = (img.format or "").upper()
    if fmt not in SUPPORTED_FORMATS:
        raise MediaRejected(
            f"Formato {fmt or 'desconhecido'} não suportado. Usa JPG, PNG ou WEBP."
        )

    width, height = img.size
    if max(width, height) > settings.MEDIA_MAX_DIMENSION:
        raise MediaRejected(
            f"A imagem tem {width}×{height}px e o limite é "
            f"{settings.MEDIA_MAX_DIMENSION}px."
        )
    if min(width, height) < settings.MEDIA_MIN_DIMENSION:
        raise MediaRejected(
            f"A imagem é pequena demais ({width}×{height}px). "
            f"O mínimo é {settings.MEDIA_MIN_DIMENSION}px."
        )
    return img, fmt, width, height


def _write_variants(img: Image.Image, checksum: str) -> tuple[str, dict[str, str], int]:
    """Guarda o original (normalizado) e as derivações WebP."""
    root = media_root()
    bucket = checksum[:2]
    folder = f"{bucket}/{checksum[2:4]}"
    target_dir = root / folder
    target_dir.mkdir(parents=True, exist_ok=True)

    base = img
    if base.mode in ("RGBA", "LA", "P"):
        base = base.convert("RGBA")
    elif base.mode not in ("RGB", "L"):
        base = base.convert("RGB")

    original_key = f"{folder}/{checksum}.png"
    original_path = _abspath(original_key)
    if not original_path.exists():
        base.save(original_path, format="PNG", optimize=True)

    variants: dict[str, str] = {}
    for width in settings.media_variants_list:
        if base.width < width:
            continue
        scaled = base.copy()
        scaled.thumbnail((width, width * 4), Image.LANCZOS)
        key = f"{folder}/{checksum}-{width}.{VARIANT_FORMAT}"
        path = _abspath(key)
        if not path.exists():
            saved = scaled
            if saved.mode == "RGBA":
                saved.save(path, format=VARIANT_FORMAT, quality=VARIANT_QUALITY, method=6)
            else:
                saved.convert("RGB").save(
                    path, format=VARIANT_FORMAT, quality=VARIANT_QUALITY, method=6
                )
        variants[str(width)] = key

    return original_key, variants, original_path.stat().st_size


def store_image(raw: bytes) -> StoredImage:
    """Valida e persiste. Devolve as chaves; não toca na base de dados."""
    img, fmt, width, height = validate(raw)
    checksum = hashlib.sha256(raw).hexdigest()
    storage_key, variants, size = _write_variants(img, checksum)

    mime = {
        "JPEG": "image/jpeg",
        "PNG": "image/png",
        "WEBP": "image/webp",
        "HEIF": "image/heic",
    }[fmt]

    return StoredImage(
        storage_key=storage_key,
        width=width,
        height=height,
        bytes=size,
        checksum=checksum,
        mime_type=mime,
        variants=variants,
    )


def store(
    db: Session,
    raw: bytes,
    *,
    kind: str,
    uploaded_by,
    entity_id: str | None = None,
    review_id: str | None = None,
    original_filename: str | None = None,
    source: str | None = None,
    position: int = 0,
    alt_text: str | None = None,
    auto_approve: bool = False,
) -> Media:
    """Fluxo completo: valida, guarda e cria a linha na base de dados.

    `source` decide a proveniência (§9). Sem `auto_approve`, uma foto de
    utilizador fica PENDING e não é servida como oficial.
    """
    import json as _json

    from app.core.constants import ROLE_SUPER_ADMIN, ROLE_ADMIN, ROLE_EDITOR

    stored = store_image(raw)

    if source is None:
        role = getattr(uploaded_by, "role", None)
        source = (
            MEDIA_SOURCE_OFFICIAL
            if role in (ROLE_SUPER_ADMIN, ROLE_ADMIN, ROLE_EDITOR)
            else MEDIA_SOURCE_COMMUNITY
        )

    approved_now = auto_approve or source == MEDIA_SOURCE_OFFICIAL

    # Deduplicação: o mesmo conteúdo já guardado reaproveita o registo.
    existing = (
        db.query(Media)
        .filter(
            Media.checksum == stored.checksum,
            Media.kind == kind,
            Media.entity_id == entity_id,
        )
        .first()
    )
    if existing is not None:
        return existing

    media = Media(
        entity_id=entity_id,
        review_id=review_id,
        user_id=getattr(uploaded_by, "id", None),
        kind=kind,
        source=source,
        storage_key=stored.storage_key,
        variants=_json.dumps(stored.variants) if stored.variants else None,
        original_filename=(original_filename or "")[:255] or None,
        mime_type=stored.mime_type,
        width=stored.width,
        height=stored.height,
        bytes=stored.bytes,
        checksum=stored.checksum,
        status=MEDIA_APPROVED if approved_now else MEDIA_PENDING,
        approved_by=getattr(uploaded_by, "id", None) if approved_now else None,
        approved_at=datetime.now(timezone.utc) if approved_now else None,
        position=position,
        alt_text=alt_text,
    )
    db.add(media)
    db.commit()
    db.refresh(media)

    if media.is_approved and entity_id:
        _assign_role(db, entity_id, media)
    return media


def _assign_role(db: Session, entity_id: str, media: Media) -> None:
    """Define logo, capa ou imagem principal a partir do `kind` da media."""
    from app.models.company import Company

    company = db.query(Company).filter(Company.id == entity_id).first()
    if company is None or not media.is_approved:
        return
    if media.kind == MEDIA_MAIN and not company.main_media_id:
        company.main_media_id = media.id
    elif media.kind == "LOGO" and not company.logo_media_id:
        company.logo_media_id = media.id
    elif media.kind == "COVER" and not company.cover_media_id:
        company.cover_media_id = media.id
    db.commit()


def url_for(media: Media | None, width: int = 640, use_variant: bool = True) -> str | None:
    """URL pública de uma media, preferindo sempre a versão optimizada."""
    if media is None or not media.storage_key:
        return None
    prefix = settings.MEDIA_URL_PREFIX.rstrip("/")
    if use_variant and media.variants:
        import json

        try:
            variants = json.loads(media.variants)
        except (ValueError, TypeError):
            variants = {}
        best = None
        for vw, key in variants.items():
            try:
                size = int(vw)
            except (TypeError, ValueError):
                continue
            if best is None or abs(size - width) < abs(best - width):
                best, best_key = size, key
        if best is not None:
            return f"{prefix}/{best_key}"
    return f"{prefix}/{media.storage_key}"


def url_for_id(db: Session, media_id: str | None, width: int = 640) -> str | None:
    if not media_id:
        return None
    media = db.query(Media).filter(Media.id == media_id).first()
    return url_for(media, width=width)


def delete_files(media: Media) -> None:
    """Remove os ficheiros do disco. Só remove se mais nenhum registo
    Media apontar para o mesmo checksum (imagens partilhadas)."""
    try:
        root = media_root()
        import json

        paths = [_abspath(media.storage_key)]
        if media.variants:
            try:
                for key in json.loads(media.variants).values():
                    paths.append(_abspath(key))
            except (ValueError, TypeError):
                pass
        for path in paths:
            if path.exists():
                path.unlink()
        # Remove pastas vazias
        for path in paths:
            folder = path.parent
            while folder != root and folder.is_dir():
                try:
                    next(folder.iterdir())
                    break
                except StopIteration:
                    folder.rmdir()
                    folder = folder.parent
                except OSError:
                    break
    except Exception:  # pragma: no cover
        pass
