from sqlalchemy import Boolean, Column, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class Favorite(Base, UUIDMixin, TimestampMixin):
    """Guardar uma entidade na lista do utilizador (§30)."""

    __tablename__ = "favorites"
    __table_args__ = (UniqueConstraint("user_id", "company_id", name="uq_favorite"),)

    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    company_id = Column(String(36), ForeignKey("companies.id"), nullable=False, index=True)

    user = relationship("User", back_populates="favorites")
    company = relationship("Company")


class Follow(Base, UUIDMixin, TimestampMixin):
    """Seguir uma entidade, para ser avisado de novidades (§26)."""

    __tablename__ = "follows"
    __table_args__ = (UniqueConstraint("user_id", "company_id", name="uq_follow"),)

    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    company_id = Column(String(36), ForeignKey("companies.id"), nullable=False, index=True)

    # Um perfil pode ser reavaliado, por isso o aviso distingue "nova
    # avaliação" de "nova imagem oficial".
    notify_reviews = Column(Boolean, default=True, nullable=False)
    notify_media = Column(Boolean, default=True, nullable=False)

    user = relationship("User", back_populates="following")
    company = relationship("Company")


class UserFollow(Base, UUIDMixin, TimestampMixin):
    """Seguir outra pessoa."""

    __tablename__ = "user_follows"
    __table_args__ = (UniqueConstraint("follower_id", "followee_id", name="uq_user_follow"),)

    follower_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    followee_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    follower = relationship("User", foreign_keys=[follower_id])
    followee = relationship("User", foreign_keys=[followee_id])


class ReviewVote(Base, UUIDMixin, TimestampMixin):
    """Sinalizar uma avaliação como útil ou enganosa (§25).

    Substitui o par concordar/discordar com dois botões: o valor booleano
    guarda a posição de quem votou, mas a interface só apresenta o total
    concordante, porque "12 pessoas acharam enganosa" é informação útil e
    "1 pessoa achou enganosa, 0 concordaram" só dá trabalho ao autor.
    """

    __tablename__ = "review_votes"
    __table_args__ = (UniqueConstraint("user_id", "review_id", name="uq_review_vote"),)

    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    review_id = Column(String(36), ForeignKey("reviews.id"), nullable=False, index=True)
    is_agree = Column(Boolean, nullable=False)

    user = relationship("User")
    review = relationship("Review", backref="votes")


class ReviewComment(Base, UUIDMixin, TimestampMixin):
    """Comentário a uma avaliação. Distinto de `review.comment`, que é o texto
    da própria avaliação."""

    __tablename__ = "review_comments"

    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    review_id = Column(String(36), ForeignKey("reviews.id"), nullable=False, index=True)
    content = Column(String(600), nullable=False)
    is_hidden = Column(Boolean, default=False, nullable=False)

    user = relationship("User")
    review = relationship("Review", backref="comments")
