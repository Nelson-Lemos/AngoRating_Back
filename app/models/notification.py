from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.models.base import Base, UUIDMixin, TimestampMixin


class Notification(Base, UUIDMixin, TimestampMixin):
    """Notificação. `entity_type`/`entity_id` permitem navegar para onde
    aconteceu a coisa."""

    __tablename__ = "notifications"

    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    type = Column(String(50), nullable=False, index=True)
    content = Column(Text, nullable=False)

    entity_type = Column(String(50), nullable=True)
    entity_id = Column(String(36), nullable=True)

    # Quem originou, quando a notificação é sobre outra pessoa
    actor_id = Column(String(36), ForeignKey("users.id"), nullable=True)

    is_read = Column(Boolean, default=False, nullable=False, index=True)

    # Duas FKs para `users` (destinatário e autor da notificação).
    user = relationship("User", backref="notifications", foreign_keys=[user_id])
    actor = relationship("User", foreign_keys=[actor_id])
