from sqlalchemy import Column, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship

from app.models.base import Base, UUIDMixin, TimestampMixin

# Árvore geográfica angolana. `type` hierárquico:
# COUNTRY -> PROVINCE -> MUNICIPALITY -> (placeholder) NEIGHBOURHOOD
LOCATION_TYPES = ("COUNTRY", "PROVINCE", "MUNICIPALITY", "NEIGHBOURHOOD")


class Location(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "locations"

    name = Column(String(140), nullable=False)
    slug = Column(String(140), nullable=True, index=True)
    type = Column(String(20), nullable=False, index=True)
    parent_id = Column(String(36), ForeignKey("locations.id"), nullable=True, index=True)

    parent = relationship("Location", remote_side="Location.id", backref="children")

    @property
    def path(self) -> str:
        parts = []
        node = self
        seen = set()
        while node is not None and node.id not in seen:
            seen.add(node.id)
            parts.append(node.name)
            node = node.parent
        return " › ".join(reversed(parts))
