"""Gelombang 1: review temuan, ronde retest, catatan Markdown, templat laporan berversi.

Temuan yang sudah ada sebelum migrasi ini ditandai 'approved' agar laporan lama tidak berubah isi.

Revision ID: 0002
Revises: 0001
"""
import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "retests",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("finding_id", sa.Integer, sa.ForeignKey("findings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("round_no", sa.Integer, nullable=False),
        sa.Column("result", sa.String(16), nullable=False),
        sa.Column("tested_at", sa.Date, nullable=False),
        sa.Column("notes", sa.Text, nullable=False),
        sa.Column("tester_id", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.UniqueConstraint("finding_id", "round_no"),
    )
    op.create_index("ix_retests_finding_id", "retests", ["finding_id"])

    op.create_table(
        "note_templates",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(120), nullable=False, unique=True),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("is_default", sa.Boolean, nullable=False),
        sa.Column("updated_by_id", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )

    op.create_table(
        "notes",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("engagement_id", sa.Integer, sa.ForeignKey("engagements.id", ondelete="CASCADE"), nullable=False),
        sa.Column("owner_id", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
        sa.Column("updated_by_id", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
    )
    op.create_index("ix_notes_engagement_id", "notes", ["engagement_id"])

    op.create_table(
        "note_versions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("note_id", sa.Integer, sa.ForeignKey("notes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("edited_by_id", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.UniqueConstraint("note_id", "version"),
    )
    op.create_index("ix_note_versions_note_id", "note_versions", ["note_id"])

    op.create_table(
        "report_templates",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("notes", sa.String(500), nullable=False),
        sa.Column("size", sa.Integer, nullable=False),
        sa.Column("data", sa.LargeBinary, nullable=False),
        sa.Column("created_by_id", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("activated_at", sa.DateTime, nullable=True),
        sa.UniqueConstraint("kind", "version"),
    )
    op.create_index("ix_report_templates_kind", "report_templates", ["kind"])

    op.add_column("findings", sa.Column("review_status", sa.String(24), nullable=False, server_default="draft"))
    op.add_column("findings", sa.Column("review_note", sa.Text, nullable=False, server_default=""))
    op.execute("UPDATE findings SET review_status = 'approved'")  # temuan lama dianggap sudah final

    with op.batch_alter_table("evidence") as batch:
        batch.add_column(sa.Column(
            "retest_id", sa.Integer,
            sa.ForeignKey("retests.id", ondelete="CASCADE", name="fk_evidence_retest_id"), nullable=True))
        batch.create_index("ix_evidence_retest_id", ["retest_id"])


def downgrade() -> None:
    with op.batch_alter_table("evidence") as batch:
        batch.drop_index("ix_evidence_retest_id")
        batch.drop_column("retest_id")
    op.drop_column("findings", "review_note")
    op.drop_column("findings", "review_status")
    for table in ("report_templates", "note_versions", "notes", "note_templates", "retests"):
        op.drop_table(table)
