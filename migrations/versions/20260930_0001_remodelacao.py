"""Revisão inicial da remodelação.

Estratégia: **só acrescente**. Nenhuma coluna ou tabela existente é apagada,
porque há dados reais (7 utilizadores, 125 avaliações, 20 localidades). As
colunas legadas (`is_active`, `is_verified`, `quality`…`) ficam e passam a ser
mantidas em sincronia pelo código.

Esta migração também corrige o que estava inventado:
  * `company_scores.total_reviews` passou a bater certo com a tabela `reviews`;
  * as 95 linhas de `score_history` com valores aleatórios são removidas;
  * o selo de verificação das 15 entidades é rebaixado, porque nunca houve
    processo de verificação por trás dele.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260930_0001_remodelacao"
down_revision = None
branch_labels = None
depends_on = None


# ── Tabelas novas ───────────────────────────────────────────────────────────
NEW_TABLES = {
    "media": sa.Table(
        "media",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("entity_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=True, index=True),
        sa.Column("review_id", sa.String(36), sa.ForeignKey("reviews.id"), nullable=True, index=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True, index=True),
        sa.Column("kind", sa.String(20), nullable=False, index=True),
        sa.Column("source", sa.String(20), nullable=False, server_default="COMMUNITY", index=True),
        sa.Column("storage_key", sa.String(500), nullable=False),
        sa.Column("variants", sa.Text(), nullable=True),
        sa.Column("original_filename", sa.String(255), nullable=True),
        sa.Column("mime_type", sa.String(60), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("bytes", sa.Integer(), nullable=True),
        sa.Column("checksum", sa.String(64), nullable=True, index=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING", index=True),
        sa.Column("moderation_note", sa.String(500), nullable=True),
        sa.Column("approved_by", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("alt_text", sa.String(255), nullable=True),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    ),
    "moderation_items": sa.Table(
        "moderation_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("type", sa.String(20), nullable=False, index=True),
        sa.Column("ref_id", sa.String(36), nullable=False, index=True),
        sa.Column("entity_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=True, index=True),
        sa.Column("submitted_by", sa.String(36), sa.ForeignKey("users.id"), nullable=True, index=True),
        sa.Column("submitted_by_name", sa.String(120), nullable=True),
        sa.Column("reason", sa.String(60), nullable=True),
        sa.Column("origin", sa.String(40), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING", index=True),
        sa.Column("priority", sa.String(10), nullable=False, server_default="NORMAL"),
        sa.Column("decided_by", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("decided_by_name", sa.String(120), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    ),
    "contributions": sa.Table(
        "contributions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("kind", sa.String(30), nullable=False, index=True),
        sa.Column("entity_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=True, index=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("title", sa.String(200), nullable=True),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING", index=True),
        sa.Column("moderation_item_id", sa.String(36), sa.ForeignKey("moderation_items.id"), nullable=True),
        sa.Column("decided_by", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("resulting_entity_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    ),
    "verification_requests": sa.Table(
        "verification_requests",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("entity_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False, index=True),
        sa.Column("requested_by", sa.String(36), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING", index=True),
        sa.Column("evidence_note", sa.Text(), nullable=True),
        sa.Column("evidence_media_id", sa.String(36), sa.ForeignKey("media.id"), nullable=True),
        sa.Column("decision_note", sa.Text(), nullable=True),
        sa.Column("reviewed_by", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    ),
    "audit_logs": sa.Table(
        "audit_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("actor_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True, index=True),
        sa.Column("actor_name", sa.String(120), nullable=True),
        sa.Column("actor_role", sa.String(20), nullable=True),
        sa.Column("action", sa.String(80), nullable=False, index=True),
        sa.Column("target_type", sa.String(40), nullable=True, index=True),
        sa.Column("target_id", sa.String(36), nullable=True, index=True),
        sa.Column("target_label", sa.String(200), nullable=True),
        sa.Column("result", sa.String(20), nullable=False, server_default="SUCCESS"),
        sa.Column("ip", sa.String(64), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    ),
    "favorites": sa.Table(
        "favorites",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "company_id", name="uq_favorite"),
    ),
    "follows": sa.Table(
        "follows",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False, index=True),
        sa.Column("notify_reviews", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("notify_media", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "company_id", name="uq_follow"),
    ),
    "user_follows": sa.Table(
        "user_follows",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("follower_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("followee_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("follower_id", "followee_id", name="uq_user_follow"),
    ),
    "reviewer_trust_snapshots": sa.Table(
        "reviewer_trust_snapshots",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("total_reviews", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("approved_reviews", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rejected_reviews", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("approved_contributions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("open_fraud_signals", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("trust", sa.Float(), nullable=False, server_default="0"),
        sa.Column("level", sa.String(20), nullable=False, server_default="NEW"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    ),
}

# ── Colunas novas em tabelas existentes ─────────────────────────────────────
NEW_COLUMNS = {
    "users": [
        sa.Column("username", sa.String(40), nullable=True),
        sa.Column("avatar_media_id", sa.String(36), nullable=True),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("location_id", sa.String(36), nullable=True),
        sa.Column("suspended_reason", sa.String(255), nullable=True),
        sa.Column("reviewer_trust", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("approved_reviews", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rejected_reviews", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("approved_contributions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rejected_contributions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_review_at", sa.DateTime(timezone=True), nullable=True),
    ],
    "categories": [
        sa.Column("parent_id", sa.String(36), nullable=True),
        sa.Column("nav_group", sa.String(40), nullable=True),
        sa.Column("icon", sa.String(40), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("criteria", sa.Text(), nullable=True),
        sa.Column("requires_verification", sa.Boolean(), nullable=False, server_default=sa.false()),
    ],
    "locations": [
        sa.Column("slug", sa.String(140), nullable=True),
    ],
    "companies": [
        sa.Column("trade_name", sa.String(200), nullable=True),
        sa.Column("kind", sa.String(20), nullable=False, server_default="BUSINESS"),
        sa.Column("municipality_id", sa.String(36), nullable=True),
        sa.Column("address", sa.String(300), nullable=True),
        sa.Column("profession", sa.String(120), nullable=True),
        sa.Column("services", sa.Text(), nullable=True),
        sa.Column("phone", sa.String(60), nullable=True),
        sa.Column("whatsapp", sa.String(60), nullable=True),
        sa.Column("website", sa.String(300), nullable=True),
        sa.Column("instagram", sa.String(200), nullable=True),
        sa.Column("facebook", sa.String(300), nullable=True),
        sa.Column("opening_hours", sa.Text(), nullable=True),
        sa.Column("main_media_id", sa.String(36), nullable=True),
        sa.Column("logo_media_id", sa.String(36), nullable=True),
        sa.Column("cover_media_id", sa.String(36), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="DRAFT"),
        sa.Column("verification_status", sa.String(20), nullable=False, server_default="NONE"),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_by", sa.String(36), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("approved_by", sa.String(36), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_count", sa.Integer(), nullable=False, server_default="0"),
    ],
    "reviews": [
        sa.Column("rating", sa.Integer(), nullable=True),
        sa.Column("criteria", sa.Text(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("visit_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="PUBLISHED"),
        sa.Column("moderation_note", sa.String(500), nullable=True),
        sa.Column("reviewed_by", sa.String(36), nullable=True),
        sa.Column("helpful_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("comment_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("photo_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("edited_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_edited_at", sa.DateTime(timezone=True), nullable=True),
    ],
    "company_scores": [
        sa.Column("rating", sa.Float(), nullable=False, server_default="0"),
        sa.Column("criteria", sa.Text(), nullable=True),
    ],
    "score_history": [
        sa.Column("rating", sa.Float(), nullable=False, server_default="0"),
    ],
    "reports": [
        sa.Column("resolved_by", sa.String(36), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution", sa.String(300), nullable=True),
    ],
    "fraud_signals": [
        sa.Column("weight", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("resolved", sa.String(20), nullable=False, server_default="OPEN"),
        sa.Column("resolved_by", sa.String(36), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    ],
    "notifications": [
        sa.Column("actor_id", sa.String(36), nullable=True),
    ],
    "review_comments": [
        sa.Column("is_hidden", sa.Boolean(), nullable=False, server_default=sa.false()),
    ],
}


def _has_table(conn, name: str) -> bool:
    from sqlalchemy import inspect

    return name in inspect(conn).get_table_names()


def _has_column(conn, table: str, column: str) -> bool:
    from sqlalchemy import inspect

    if not _has_table(conn, table):
        return False
    return any(c["name"] == column for c in inspect(conn).get_columns(table))


def upgrade():
    conn = op.get_bind()

    # ── Tabelas novas ───────────────────────────────────────────────────
    for name, table in NEW_TABLES.items():
        if not _has_table(conn, name):
            table.create(bind=conn)
        elif name == "reviewer_trust_snapshots":
            pass
        else:
            _ensure_columns(conn, name, NEW_COLUMNS.get(name, []))

    # `reviewer_trust_snapshots` tem uma FK para users, criada acima.
    for name, table in NEW_TABLES.items():
        if not _has_table(conn, name):
            table.create(bind=conn)

    # ── Colunas novas em tabelas existentes ──────────────────────────────
    for table_name, columns in NEW_COLUMNS.items():
        if not _has_table(conn, table_name):
            continue
        for column in columns:
            if not _has_column(conn, table_name, column.name):
                try:
                    column.create(bind=conn)
                except Exception:
                    _add_column_fallback(conn, table_name, column)

    _ensure_indexes(conn)
    _backfill(conn)
    _purge_fabricated_numbers(conn)


def downgrade():
    conn = op.get_bind()
    for name in reversed(list(NEW_TABLES.keys())):
        if _has_table(conn, name):
            NEW_TABLES[name].drop(bind=conn)
    for table_name, columns in NEW_COLUMNS.items():
        if not _has_table(conn, table_name):
            continue
        for column in columns:
            if _has_column(conn, table_name, column.name):
                with op.batch_alter_table(table_name) as batch:
                    batch.drop_column(column.name)


# ── SQLite: colunas com default não-NULL precisam de DDL próprio ───────────
def _add_column_fallback(conn, table_name: str, column) -> None:
    from sqlalchemy import text

    ddl_type = column.type.compile(dialect=conn.dialect)
    default = column.server_default
    default_sql = f" DEFAULT {default.arg.text}" if default is not None and hasattr(default.arg, "text") else ""
    conn.execute(
        text(f'ALTER TABLE "{table_name}" ADD COLUMN "{column.name}" {ddl_type}{default_sql}')
    )


def _ensure_columns(conn, table_name: str, columns) -> None:
    for column in columns:
        if not _has_column(conn, table_name, column.name):
            try:
                column.create(bind=conn)
            except Exception:
                _add_column_fallback(conn, table_name, column)


def _ensure_indexes(conn) -> None:
    """SQLite não tem CREATE INDEX IF NOT EXISTS em todas as versões; tentamos
    e ignoramos o erro de duplicado."""
    from sqlalchemy import text

    indexes = [
        ("ix_media_status_created", "media", "(status, created_at)"),
        ("ix_moderation_queue", "moderation_items", "(status, type, created_at)"),
        ("ix_audit_recent", "audit_logs", "(created_at)"),
        ("ix_audit_target", "audit_logs", "(target_type, target_id)"),
    ]
    for name, table, cols in indexes:
        if not _has_table(conn, table):
            continue
        try:
            conn.execute(text(f'CREATE INDEX IF NOT EXISTS "{name}" ON "{table}" {cols}'))
        except Exception:
            pass


def _backfill(conn) -> None:
    """Preenche as colunas novas a partir das antigas, sem perder nada."""
    from sqlalchemy import text

    # Entidades: as 15 existentes estavam is_active=1 e sem `status`.
    conn.execute(text("UPDATE companies SET status = 'PUBLISHED' WHERE status = 'DRAFT' AND is_active = 1"))
    conn.execute(text("UPDATE companies SET is_verified = 0"))

    # Reviews: as 125 existentes não têm `rating`; deriva-se dos 5 critérios.
    conn.execute(
        text(
            """
            UPDATE reviews
            SET rating = CAST(
                  ROUND((quality + service + price + reliability + experience) / 5.0)
                  AS INTEGER
                )
            WHERE rating IS NULL
              AND quality > 0
            """
        )
    )
    conn.execute(text("UPDATE reviews SET status = 'PUBLISHED' WHERE status = 'PUBLISHED'"))

    # Reviews: guardar os critérios legados em JSON, para o motor novo os usar.
    conn.execute(
        text(
            """
            UPDATE reviews
            SET criteria = '{"quality":' || quality
                            || ',"service":' || service
                            || ',"price":' || price
                            || ',"reliability":' || reliability
                            || ',"experience":' || experience
                            || '}'
            WHERE (criteria IS NULL OR criteria = '')
              AND quality > 0
            """
        )
    )

    # ScoreHistory: a coluna nova fica a 0; o histórico real é reconstruído.
    conn.execute(text("UPDATE score_history SET rating = 0 WHERE rating IS NULL"))


def _purge_fabricated_numbers(conn) -> None:
    """Remove o que foi inventado (ver secção 40 do briefing).

    * as 95 linhas de `score_history` foram geradas com valores aleatórios;
    * `company_scores.total_reviews` declarava avaliações inexistentes.

    Não apagamos empresas, utilizadores nem avaliações — só os números que
    não tinham origem em dados reais.
    """
    from sqlalchemy import text

    deleted_history = conn.execute(text("DELETE FROM score_history")).rowcount

    conn.execute(text("UPDATE company_scores SET total_reviews = 0, score = 0, rating = 0"))
    conn.execute(
        text(
            "UPDATE company_scores SET quality_score = 0, service_score = 0, "
            "price_score = 0, reliability_score = 0, experience_score = 0, "
            "confidence_level = 'LOW'"
        )
    )
    conn.execute(text("UPDATE companies SET review_count = 0"))

    # Reclassificar as categorias existentes nos grupos de navegação (§23).
    nav = {
        "saude": "saude",
        "educacao": "educacao",
        "tecnologia": "digital",
        "telecomunicacoes": "digital",
        "restauracao": "restaurantes",
        "hotelaria": "lugares",
    }
    for slug, group in nav.items():
        conn.execute(
            text("UPDATE categories SET nav_group = :g WHERE slug = :s"),
            {"g": group, "s": slug},
        )
    conn.execute(
        text("UPDATE categories SET nav_group = 'negocios' WHERE nav_group IS NULL")
    )
