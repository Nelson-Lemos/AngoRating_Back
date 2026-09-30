from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship

from app.core.constants import (
    MEDIA_APPROVED, MEDIA_SOURCE_COMMUNITY, MEDIA_SOURCE_OFFICIAL,
    MEDIA_PENDING,
)
from app.models.base import Base, UUIDMixin, TimestampMixin


class Media(Base, UUIDMixin, TimestampMixin):
    """Uma imagem. Nunca se aponta `company.logo` directamente para um
    ficheiro: aponta-se para um `Media`, que carrega autoria, proveniência e
    estado de moderação.

    `source` distingue imagem oficial (admin / proprietário verificado) de
    imagem comunitária (§9). `status` impede que uma foto de utilizador seja
    servida como oficial sem passar por moderação.
    """

    __tablename__ = "media"

    # Dono do conteúdo. Todos opcionais: uma foto de avatar só tem user_id,
    # uma foto de capa só tem entity_id.
    entity_id = Column(String(36), ForeignKey("companies.id"), nullable=True, index=True)
    review_id = Column(String(36), ForeignKey("reviews.id"), nullable=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)

    kind = Column(String(20), nullable=False, index=True)
    source = Column(
        String(20),
        default=MEDIA_SOURCE_COMMUNITY,
        nullable=False,
        index=True,
    )

    # Caminho relativo dentro de MEDIA_ROOT. Nunca um caminho absoluto nem URL.
    storage_key = Column(String(500), nullable=False)
    # Derivações: {"320": "ab/cd/abcd.webp", "640": ...}
    variants = Column(Text, nullable=True)

    original_filename = Column(String(255), nullable=True)
    mime_type = Column(String(60), nullable=False)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    bytes = Column(Integer, nullable=True)
    checksum = Column(String(64), nullable=True, index=True)

    status = Column(String(20), default=MEDIA_PENDING, nullable=False, index=True)
    moderation_note = Column(String(500), nullable=True)
    approved_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)

    # Ordem dentro da galeria (§15).
    position = Column(Integer, default=0, nullable=False)

    alt_text = Column(String(255), nullable=True)
    is_public = Column(Boolean, default=True, nullable=False)

    uploader = relationship("User", back_populates="media", foreign_keys=[user_id])
    entity = relationship("Company", back_populates="media")
    review = relationship("Review", back_populates="media")

    @property
    def is_approved(self) -> bool:
        return self.status == MEDIA_APPROVED

    @property
    def is_official(self) -> bool:
        return self.source == MEDIA_SOURCE_OFFICIAL
