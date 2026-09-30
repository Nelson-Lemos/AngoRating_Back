from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.constants import ROLE_PERMISSIONS, STAFF_ROLES
from app.core.database import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
oauth2_scheme_optional = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login", auto_error=False
)

MIN_PASSWORD_LENGTH = 8
_BCRYPT_MAX_BYTES = 72


# ── Palavras-passe ──────────────────────────────────────────────────────────
def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8")[:_BCRYPT_MAX_BYTES],
            hashed_password.encode("utf-8"),
        )
    except (ValueError, TypeError):
        return False


def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(
        password.encode("utf-8")[:_BCRYPT_MAX_BYTES], bcrypt.gensalt()
    ).decode("utf-8")


def password_problems(password: str) -> list[str]:
    """Regras mínimas. Devolve uma lista de problemas (vazia = aceitável)."""
    problems = []
    if len(password) < MIN_PASSWORD_LENGTH:
        problems.append(f"deve ter pelo menos {MIN_PASSWORD_LENGTH} caracteres")
    if password.isdigit() or password.isalpha():
        problems.append("deve combinar letras e números")
    if password.lower() in {
        "password", "angorating", "12345678", "qwertyui", "admin123", "user123",
    }:
        problems.append("é demasiado comum")
    return problems


# ── Tokens ──────────────────────────────────────────────────────────────────
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    # `jti` permite revogar um refresh token específico mais tarde.
    to_encode.update(
        {
            "exp": expire,
            "type": "refresh",
            "jti": __import__("uuid").uuid4().hex,
        }
    )
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessão expirada. Inicia sessão novamente.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessão inválida.",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ── Dependências ────────────────────────────────────────────────────────────
def _load_user(db: Session, user_id: str):
    from app.models.user import User

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=401, detail="Conta não encontrada.")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Esta conta está desactivada.")
    return user


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
):
    payload = decode_token(token)
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Tipo de token inválido.")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Sessão inválida.")
    return _load_user(db, user_id)


def get_current_active_user(current_user=Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(status_code=403, detail="Esta conta está desactivada.")
    return current_user


def get_optional_user(
    token: Optional[str] = Depends(oauth2_scheme_optional),
    db: Session = Depends(get_db),
):
    """Pedido anónimo aceite. Devolve None em vez de falhar."""
    from app.models.user import User

    if not token:
        return None
    try:
        payload = decode_token(token)
    except HTTPException:
        return None
    if payload.get("type") != "access":
        return None
    user_id = payload.get("sub")
    if not user_id:
        return None
    user = db.query(User).filter(User.id == user_id).first()
    if user is None or not user.is_active:
        return None
    return user


def permissions_for(role: str) -> frozenset[str]:
    return ROLE_PERMISSIONS.get(role, frozenset())


def has_permission(user, permission: str) -> bool:
    if user is None:
        return False
    return permission in permissions_for(user.role)


def require_permission(permission: str):
    """Dependência FastAPI que exige uma permissão específica (§38).

    Verifica sempre no servidor — nunca confiar no `role` que vem no token,
    porque esse valor envelhece se a pessoa for promovida ou despromovida.
    """

    def _dependency(current_user=Depends(get_current_active_user)):
        if not has_permission(current_user, permission):
            raise HTTPException(
                status_code=403,
                detail="Não tem permissão para esta acção.",
            )
        return current_user

    return _dependency


def require_staff(current_user=Depends(get_current_active_user)):
    if current_user.role not in STAFF_ROLES:
        raise HTTPException(status_code=403, detail="Acesso restrito à equipa.")
    return current_user


# Legado: existia como `require_admin`. Mantém o mesmo contrato mas passa a
# verificar a permissão real, e só o SUPER_ADMIN/ADMIN a satisfazem.
def require_admin(current_user=Depends(get_current_active_user)):
    if current_user.role not in ("SUPER_ADMIN", "ADMIN"):
        raise HTTPException(status_code=403, detail="Acesso restrito a administradores.")
    return current_user
