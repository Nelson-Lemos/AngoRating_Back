from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey, Integer
from sqlalchemy.orm import relationship

from app.core.constants import (
    KIND_BUSINESS, STATUS_PUBLISHED, VERIF_NONE,
)
from app.models.base import Base, UUIDMixin, TimestampMixin


class Company(Base, UUIDMixin, TimestampMixin):
    """Uma entidade avaliável — o modelo é genérico de propósito (§3).

    O nome histórico da tabela é `companies`, mas o registo pode ser uma
    empresa, um prestador informal, um lugar, um produto, um criador, um
    artista, uma app, um site ou um evento. `kind` diz qual é.
    A verificação é um processo, não um booleano (§17).
    """

    __tablename__ = "companies"

    name = Column(String(200), nullable=False, index=True)
    trade_name = Column(String(200), nullable=True)
    slug = Column(String(200), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)

    kind = Column(String(20), default=KIND_BUSINESS, nullable=False, index=True)

    category_id = Column(String(36), ForeignKey("categories.id"), nullable=False, index=True)
    # `location_id` = província (ou país, para entidades nacionais)
    location_id = Column(String(36), ForeignKey("locations.id"), nullable=False, index=True)
    municipality_id = Column(String(36), ForeignKey("locations.id"), nullable=True, index=True)
    address = Column(String(300), nullable=True)

    # Para `kind == PROFESSIONAL`: ofício e zona de trabalho.
    profession = Column(String(120), nullable=True, index=True)
    services = Column(Text, nullable=True)

    # Contacto (§13)
    phone = Column(String(60), nullable=True)
    whatsapp = Column(String(60), nullable=True)
    website = Column(String(300), nullable=True)
    instagram = Column(String(200), nullable=True)
    facebook = Column(String(300), nullable=True)
    opening_hours = Column(Text, nullable=True)

    # Imagens: ponteiros para `media`, nunca ficheiros (§5)
    main_media_id = Column(String(36), nullable=True, index=True)
    logo_media_id = Column(String(36), nullable=True)
    cover_media_id = Column(String(36), nullable=True)

    # Ciclo de vida
    status = Column(String(20), default="DRAFT", nullable=False, index=True)
    verification_status = Column(String(20), default=VERIF_NONE, nullable=False, index=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    verified_by = Column(String(36), ForeignKey("users.id"), nullable=True)

    # Autoria — quem criou e quem aprovou (§6, §7)
    created_by = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    approved_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)

    # Proprietário / representante autorizado (§45)
    owner_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)

    # Legado — mantidos e mantidos em sincronia com status/verification_status
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    is_verified = Column(Boolean, default=False, nullable=False)

    # Contadores desnormalizados para ordenação rápida
    review_count = Column(Integer, default=0, nullable=False)

    category = relationship(
        "Category", back_populates="companies", foreign_keys=[category_id]
    )
    location = relationship("Location", foreign_keys=[location_id])
    municipality = relationship("Location", foreign_keys=[municipality_id])
    owner = relationship("User", foreign_keys=[owner_id], backref="owned_entities")
    media = relationship(
        "Media",
        back_populates="entity",
        cascade="all, delete-orphan",
        order_by="Media.position",
    )
    reviews = relationship("Review", back_populates="company")
    score = relationship(
        "CompanyScore", back_populates="company", uselist=False, cascade="all, delete-orphan"
    )
    score_history = relationship(
        "ScoreHistory", back_populates="company", cascade="all, delete-orphan"
    )
    verifications = relationship(
        "VerificationRequest", back_populates="entity", cascade="all, delete-orphan"
    )

    @property
    def is_published(self) -> bool:
        return self.status == STATUS_PUBLISHED and self.is_active

    @property
    def is_verified_entity(self) -> bool:
        return self.verification_status == "VERIFIED"

    def sync_legacy_flags(self) -> None:
        """Mantém `is_active`/`is_verified` alinhados com as colunas novas,
        para que rotas legadas continuem a comportar-se correctamente."""
        self.is_active = self.status in (STATUS_PUBLISHED, STATUS_SUSPENDED)
        self.is_verified = self.verification_status == "VERIFIED"


# `Entity` é o nome de domínio. `Company` mantém-se por compatibilidade com as
# rotas e tabelas existentes.
Entity = Company
