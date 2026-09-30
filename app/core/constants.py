"""Constantes de domínio do AngoRating.

Tudo o que é um valor fechado (papéis, estados, tipos) vive aqui para que
frontend, backend e migrações partilhem a mesma verdade.
"""
from __future__ import annotations

# ── Papéis (RBAC) ────────────────────────────────────────────────────────────
ROLE_SUPER_ADMIN = "SUPER_ADMIN"
ROLE_ADMIN = "ADMIN"
ROLE_MODERATOR = "MODERATOR"
ROLE_EDITOR = "EDITOR"
ROLE_USER = "USER"

ALL_ROLES = (ROLE_SUPER_ADMIN, ROLE_ADMIN, ROLE_MODERATOR, ROLE_EDITOR, ROLE_USER)
STAFF_ROLES = (ROLE_SUPER_ADMIN, ROLE_ADMIN, ROLE_MODERATOR, ROLE_EDITOR)

# Permissões
PERM_CATALOG_MANAGE = "catalog.manage"      # criar/editar/entidades/categorias
PERM_CATALOG_PUBLISH = "catalog.publish"    # publicar, despublicar, suspender
PERM_MEDIA_MANAGE = "media.manage"          # aprovar/rejeitar/eliminar media
PERM_REVIEW_MODERATE = "review.moderate"    # invalidar avaliações
PERM_REPORT_HANDLE = "report.handle"        # tratar denúncias
PERM_VERIFICATION_DECIDE = "verification.decide"
PERM_USER_MANAGE = "user.manage"
PERM_ADMIN_MANAGE = "admin.manage"          # criar/promover administradores
PERM_SETTINGS_MANAGE = "settings.manage"
PERM_AUDIT_READ = "audit.read"
PERM_ANALYTICS_READ = "analytics.read"

ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    ROLE_SUPER_ADMIN: frozenset(
        {
            PERM_CATALOG_MANAGE, PERM_CATALOG_PUBLISH, PERM_MEDIA_MANAGE,
            PERM_REVIEW_MODERATE, PERM_REPORT_HANDLE, PERM_VERIFICATION_DECIDE,
            PERM_USER_MANAGE, PERM_ADMIN_MANAGE, PERM_SETTINGS_MANAGE,
            PERM_AUDIT_READ, PERM_ANALYTICS_READ,
        }
    ),
    ROLE_ADMIN: frozenset(
        {
            PERM_CATALOG_MANAGE, PERM_CATALOG_PUBLISH, PERM_MEDIA_MANAGE,
            PERM_REVIEW_MODERATE, PERM_REPORT_HANDLE, PERM_VERIFICATION_DECIDE,
            PERM_USER_MANAGE, PERM_SETTINGS_MANAGE, PERM_AUDIT_READ,
            PERM_ANALYTICS_READ,
        }
    ),
    ROLE_MODERATOR: frozenset(
        {PERM_MEDIA_MANAGE, PERM_REVIEW_MODERATE, PERM_REPORT_HANDLE}
    ),
    ROLE_EDITOR: frozenset({PERM_CATALOG_MANAGE}),
    ROLE_USER: frozenset(),
}

# ── Entidades ───────────────────────────────────────────────────────────────
KIND_BUSINESS = "BUSINESS"
KIND_PROFESSIONAL = "PROFESSIONAL"
KIND_PLACE = "PLACE"
KIND_PRODUCT = "PRODUCT"
KIND_CREATOR = "CREATOR"
KIND_ARTIST = "ARTIST"
KIND_APP = "APP"
KIND_SITE = "SITE"
KIND_EVENT = "EVENT"

ALL_KINDS = (
    KIND_BUSINESS, KIND_PROFESSIONAL, KIND_PLACE, KIND_PRODUCT,
    KIND_CREATOR, KIND_ARTIST, KIND_APP, KIND_SITE, KIND_EVENT,
)

# ── Estado de publicação de uma entidade ────────────────────────────────────
STATUS_DRAFT = "DRAFT"
STATUS_PENDING = "PENDING"
STATUS_PUBLISHED = "PUBLISHED"
STATUS_SUSPENDED = "SUSPENDED"
STATUS_ARCHIVED = "ARCHIVED"

ALL_ENTITY_STATUSES = (
    STATUS_DRAFT, STATUS_PENDING, STATUS_PUBLISHED, STATUS_SUSPENDED, STATUS_ARCHIVED,
)

# ── Verificação ─────────────────────────────────────────────────────────────
VERIF_NONE = "NONE"
VERIF_IN_REVIEW = "IN_REVIEW"
VERIF_VERIFIED = "VERIFIED"
VERIF_REJECTED = "REJECTED"

# ── Avaliações ──────────────────────────────────────────────────────────────
REVIEW_PENDING = "PENDING"
REVIEW_PUBLISHED = "PUBLISHED"
REVIEW_REJECTED = "REJECTED"
REVIEW_SUSPENDED = "SUSPENDED"

# ── Media ───────────────────────────────────────────────────────────────────
MEDIA_MAIN = "MAIN"        # imagem principal
MEDIA_LOGO = "LOGO"
MEDIA_COVER = "COVER"
MEDIA_GALLERY = "GALLERY"
MEDIA_REVIEW_PHOTO = "REVIEW_PHOTO"
MEDIA_AVATAR = "AVATAR"
MEDIA_DOCUMENT = "DOCUMENT"   # evidência de verificação

MEDIA_KINDS = (
    MEDIA_MAIN, MEDIA_LOGO, MEDIA_COVER, MEDIA_GALLERY,
    MEDIA_REVIEW_PHOTO, MEDIA_AVATAR, MEDIA_DOCUMENT,
)

MEDIA_SOURCE_OFFICIAL = "OFFICIAL"    # admin ou proprietário verificado
MEDIA_SOURCE_COMMUNITY = "COMMUNITY"  # utilizador comum

MEDIA_PENDING = "PENDING"
MEDIA_APPROVED = "APPROVED"
MEDIA_REJECTED = "REJECTED"
MEDIA_SUSPENDED = "SUSPENDED"

# ── Moderação ───────────────────────────────────────────────────────────────
MOD_ENTITY = "ENTITY"
MOD_MEDIA = "MEDIA"
MOD_REVIEW = "REVIEW"
MOD_REPORT = "REPORT"
MOD_SUGGESTION = "SUGGESTION"
MOD_VERIFICATION = "VERIFICATION"

MOD_TYPES = (
    MOD_ENTITY, MOD_MEDIA, MOD_REVIEW, MOD_REPORT, MOD_SUGGESTION, MOD_VERIFICATION,
)

MOD_PENDING = "PENDING"
MOD_APPROVED = "APPROVED"
MOD_REJECTED = "REJECTED"
MOD_NEEDS_FIX = "NEEDS_FIX"
MOD_SUSPENDED = "SUSPENDED"

# ── Contribuições da comunidade ──────────────────────────────────────────────
CONTRIB_NEW_ENTITY = "NEW_ENTITY"
CONTRIB_SUGGESTED_EDIT = "SUGGESTED_EDIT"
CONTRIB_NEW_MEDIA = "NEW_MEDIA"

# ── Motivos de denúncia ──────────────────────────────────────────────────────
REPORT_REASONS = (
    "SPAM",
    "FALSE_CONTENT",
    "OFFENSIVE_SPEECH",
    "CONFLICT_OF_INTEREST",
    "PERSONAL_DATA",
    "FRAUD",
    "OTHER",
)

# ── Angola: províncias (19) ─────────────────────────────────────────────────
ANGOLA_PROVINCES = (
    "Bengo", "Benguela " + "Bi" + "é", "Cabinda", "Cuando-Cubango",
    "Cuanza Norte", "Cuanza Sul", "Cunene", "Huambo", "Hu" + "í" + "la",
    "Icolo e Bengo", "Luanda", "Lunda Norte", "Lunda Sul",
    "Malanje", "Moxico", "Namibe", "U" + "í" + "ge", "Zaire",
)
