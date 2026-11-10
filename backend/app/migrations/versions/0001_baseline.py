"""Baseline: skema SCOPELINE v1.0 (termasuk evidence.data untuk bukti-di-database).

Database yang dibuat oleh versi lama (create_all) di-stamp ke revisi ini oleh app/migrate.py.

Revision ID: 0001
Revises:
"""
import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("username", sa.String(64), nullable=False),
        sa.Column("full_name", sa.String(120), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False),
        sa.Column("failed_attempts", sa.Integer, nullable=False),
        sa.Column("locked_until", sa.DateTime, nullable=True),
        sa.Column("totp_secret", sa.String(64), nullable=True),
        sa.Column("totp_enabled", sa.Boolean, nullable=False),
        sa.Column("token_version", sa.Integer, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    op.create_table(
        "engagements",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("client", sa.String(200), nullable=False),
        sa.Column("scope", sa.Text, nullable=False),
        sa.Column("start_date", sa.Date, nullable=False),
        sa.Column("end_date", sa.Date, nullable=False),
        sa.Column("roe_text", sa.Text, nullable=False),
        sa.Column("roe_approved", sa.Boolean, nullable=False),
        sa.Column("roe_approved_by_id", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("roe_approved_at", sa.DateTime, nullable=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("created_by_id", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )

    op.create_table(
        "engagement_members",
        sa.Column("engagement_id", sa.Integer, sa.ForeignKey("engagements.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    )

    op.create_table(
        "findings",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("engagement_id", sa.Integer, sa.ForeignKey("engagements.id", ondelete="CASCADE"), nullable=False),
        sa.Column("number", sa.Integer, nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("impact", sa.Text, nullable=False),
        sa.Column("recommendation", sa.Text, nullable=False),
        sa.Column("cvss_vector", sa.String(80), nullable=False),
        sa.Column("cvss_score", sa.Float, nullable=False),
        sa.Column("severity", sa.String(12), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("retest_notes", sa.Text, nullable=False),
        sa.Column("due_date", sa.Date, nullable=True),
        sa.Column("created_by_id", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
        sa.UniqueConstraint("engagement_id", "number"),
    )
    op.create_index("ix_findings_engagement_id", "findings", ["engagement_id"])

    op.create_table(
        "evidence",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("finding_id", sa.Integer, sa.ForeignKey("findings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("stored_name", sa.String(64), nullable=False),
        sa.Column("content_type", sa.String(64), nullable=False),
        sa.Column("size", sa.Integer, nullable=False),
        sa.Column("data", sa.LargeBinary, nullable=True),
        sa.Column("uploaded_by_id", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("uploaded_at", sa.DateTime, nullable=False),
    )
    op.create_index("ix_evidence_finding_id", "evidence", ["finding_id"])

    op.create_table(
        "finding_templates",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("impact", sa.Text, nullable=False),
        sa.Column("recommendation", sa.Text, nullable=False),
        sa.Column("cvss_vector", sa.String(80), nullable=False),
    )

    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("user_id", sa.Integer, nullable=True),
        sa.Column("username", sa.String(64), nullable=False),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("entity", sa.String(32), nullable=False),
        sa.Column("entity_id", sa.Integer, nullable=True),
        sa.Column("detail", sa.String(1000), nullable=False),
    )
    op.create_index("ix_audit_log_created_at", "audit_log", ["created_at"])


def downgrade() -> None:
    for table in ("audit_log", "finding_templates", "evidence", "findings",
                  "engagement_members", "engagements", "users"):
        op.drop_table(table)
