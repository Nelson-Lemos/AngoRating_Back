from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey, Integer
from sqlalchemy.orm import relationship

from app.models.base import Base, UUIDMixin, TimestampMixin

# Grupos de navegação de topo (§23). Um `nav_group` agrupa sectores para a
# homepage; `parent_id` serve as subcategorias (§13).
NAV_GROUPS = (
    "negocios",
    "profissionais",
    "restaurantes",
    "lugares",
    "criadores",
    "artistas",
    "produtos",
    "educacao",
    "saude",
    "digital",
)

# Critérios por defeito quando a categoria não define os seus.
DEFAULT_CRITERIA = [
    {"key": "quality", "label": "Qualidade", "weight": 0.20},
    {"key": "service", "label": "Atendimento", "weight": 0.20},
    {"key": "price", "label": "Preço", "weight": 0.15},
    {"key": "reliability", "label": "Confiabilidade", "weight": 0.25},
    {"key": "experience", "label": "Experiência", "weight": 0.20},
]


class Category(Base, UUIDMixin, TimestampMixin):
    """Sector avaliável. `nav_group` decide onde aparece na navegação."""

    __tablename__ = "categories"

    name = Column(String(100), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)

    parent_id = Column(String(36), ForeignKey("categories.id"), nullable=True, index=True)
    nav_group = Column(String(40), nullable=True, index=True)
    icon = Column(String(40), nullable=True)
    position = Column(Integer, default=0, nullable=False)

    # Critérios específicos desta categoria (§18). Lista de
    # {"key": str, "label": str, "weight": float}. NULL = usar DEFAULT_CRITERIA.
    criteria = Column(Text, nullable=True)

    # Entidades desta categoria precisam de verificação para receber selo.
    requires_verification = Column(Boolean, default=False, nullable=False)

    is_active = Column(Boolean, default=True, nullable=False)

    companies = relationship(
        "Company",
        back_populates="category",
        foreign_keys="Company.category_id",
    )
    children = relationship(
        "Category",
        backref="parent",
        remote_side="Category.id",
        lazy="selectin",
    )

    def criteria_list(self) -> list[dict]:
        import json

        if not self.criteria:
            return DEFAULT_CRITERIA
        try:
            data = json.loads(self.criteria)
        except (ValueError, TypeError):
            return DEFAULT_CRITERIA
        if not isinstance(data, list) or not data:
            return DEFAULT_CRITERIA
        return data
