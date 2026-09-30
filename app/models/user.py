from sqlalchemy import Column, String, Boolean, DateTime, Text, Integer, ForeignKey
from sqlalchemy.orm import relationship

from app.core.constants import ROLE_USER
from app.models.base import Base, UUIDMixin, TimestampMixin, utcnow


class User(Base, UUIDMixin, TimestampMixin):
    """Conta da comunidade.

    `role` rege o RBAC (ver app.core.constants.ROLE_PERMISSIONS).
    Um `User` nunca é uma entidade avaliável — quem tem perfil público é uma
    Entidade com `owner_id` a apontar para aqui.
    """

    __tablename__ = "users"

    name = Column(String(120), nullable=False)
    username = Column(String(40), unique=True, nullable=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)

    avatar_media_id = Column(
        String(36), ForeignKey("media.id", use_alter=True), nullable=True
    )
    bio = Column(Text, nullable=True)
    location_id = Column(String(36), ForeignKey("locations.id"), nullable=True)

    role = Column(String(20), default=ROLE_USER, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)

    # Sinaliza conta Suspensa por moderação, sem perder o histórico.
    suspended_reason = Column(String(255), nullable=True)

    # ── Reputação de avaliador (§27) ───────────────────────────────────────
    # Deriva de comportamento real, nunca de XP atribuído à mão.
    reviewer_trust = Column(Integer, default=0, nullable=False)
    approved_reviews = Column(Integer, default=0, nullable=False)
    rejected_reviews = Column(Integer, default=0, nullable=False)
    approved_contributions = Column(Integer, default=0, nullable=False)
    rejected_contributions = Column(Integer, default=0, nullable=False)
    last_review_at = Column(DateTime(timezone=True), nullable=True)

    # `Review` tem duas FKs para `users` (autor e moderador), por isso o
    # caminho tem de ser explícito nos dois sentidos.
    reviews = relationship(
        "Review", back_populates="user", foreign_keys="Review.user_id"
    )
    reports = relationship(
        "Report", back_populates="user", foreign_keys="Report.user_id"
    )
    media = relationship("Media", back_populates="uploader", foreign_keys="Media.user_id")
    contributions = relationship(
        "Contribution",
        back_populates="user",
        foreign_keys="Contribution.user_id",
    )
    verification_requests = relationship(
        "VerificationRequest",
        back_populates="requester",
        foreign_keys="VerificationRequest.requested_by",
    )
    trust_snapshots = relationship(
        "ReviewerTrustSnapshot",
        back_populates="user",
        foreign_keys="ReviewerTrustSnapshot.user_id",
    )
    favorites = relationship("Favorite", back_populates="user")
    following = relationship(
        "Follow", back_populates="user", foreign_keys="Follow.user_id"
    )

    @property
    def is_staff(self) -> bool:
        return self.role in ("SUPER_ADMIN", "ADMIN", "MODERATOR", "EDITOR")
