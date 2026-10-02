"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-10-02
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def _json():
    return sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "sessions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("owner_uid", sa.String(64), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("experiment", sa.String(16), nullable=False),
        sa.Column("metadata", _json(), nullable=False),
        sa.Column("exercise_id", sa.String(64), nullable=True),
        sa.Column("image_blob", sa.String(300), nullable=True),
        sa.Column("image_media_type", sa.String(40), nullable=True),
        sa.Column("peaks", _json(), nullable=False),
        sa.Column("chem_state", _json(), nullable=False),
        sa.Column("assist_mode", sa.String(16), nullable=False),
        sa.Column("turn_lock_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_sessions_owner_uid", "sessions", ["owner_uid"])
    op.create_index("ix_sessions_updated_at", "sessions", ["updated_at"])
    op.create_table(
        "messages",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("session_id", sa.Uuid(), sa.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("content", _json(), nullable=False),
        sa.Column("display_text", sa.Text(), nullable=True),
        sa.Column("mode", sa.String(16), nullable=True),
        sa.Column("usage", _json(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("session_id", "seq", name="uq_messages_session_seq"),
    )
    op.create_index("ix_messages_session_id", "messages", ["session_id"])
    op.create_table(
        "structure_checks",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("session_id", sa.Uuid(), sa.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("smiles", sa.String(300), nullable=False),
        sa.Column("result", _json(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_structure_checks_session_id", "structure_checks", ["session_id"])
    op.create_table(
        "rate_events",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True),
        sa.Column("key", sa.String(120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_rate_events_key", "rate_events", ["key"])
    op.create_index("ix_rate_events_created_at", "rate_events", ["created_at"])


def downgrade() -> None:
    op.drop_table("rate_events")
    op.drop_table("structure_checks")
    op.drop_table("messages")
    op.drop_table("sessions")
