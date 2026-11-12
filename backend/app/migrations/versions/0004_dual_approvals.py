"""Require dual RoE and final report approvals.

Revision ID: 0004
Revises: 0003
"""
import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        # SQLite supports ADD COLUMN ... REFERENCES when the new column is nullable.
        # Raw DDL avoids Alembic's unsupported separate ALTER CONSTRAINT operation and
        # preserves existing engagement/finding rows (no table rebuild/cascade).
        op.execute("ALTER TABLE engagements ADD COLUMN roe_project_manager_approved_by_id INTEGER REFERENCES users(id)")
        op.execute("ALTER TABLE engagements ADD COLUMN roe_project_manager_approved_at DATETIME")
        op.execute("ALTER TABLE engagements ADD COLUMN roe_head_approved_by_id INTEGER REFERENCES users(id)")
        op.execute("ALTER TABLE engagements ADD COLUMN roe_head_approved_at DATETIME")
    else:
        op.add_column("engagements", sa.Column(
            "roe_project_manager_approved_by_id", sa.Integer(),
            sa.ForeignKey("users.id"), nullable=True))
        op.add_column("engagements", sa.Column(
            "roe_project_manager_approved_at", sa.DateTime(), nullable=True))
        op.add_column("engagements", sa.Column(
            "roe_head_approved_by_id", sa.Integer(),
            sa.ForeignKey("users.id"), nullable=True))
        op.add_column("engagements", sa.Column(
            "roe_head_approved_at", sa.DateTime(), nullable=True))
    # Approval v1 tidak membuktikan persetujuan kedua pejabat; minta persetujuan ulang.
    op.execute(sa.text(
        "UPDATE engagements SET roe_approved = FALSE, roe_approved_by_id = NULL, roe_approved_at = NULL"
    ))
    op.create_table(
        "report_approvals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("engagement_id", sa.Integer(), sa.ForeignKey("engagements.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("approver_role", sa.String(length=16), nullable=False),
        sa.Column("approved_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("approved_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("engagement_id", "kind", "approver_role", name="uq_report_approval_role"),
    )
    op.create_index("ix_report_approvals_engagement_id", "report_approvals", ["engagement_id"])


def downgrade() -> None:
    op.drop_index("ix_report_approvals_engagement_id", table_name="report_approvals")
    op.drop_table("report_approvals")
    op.drop_column("engagements", "roe_head_approved_at")
    op.drop_column("engagements", "roe_head_approved_by_id")
    op.drop_column("engagements", "roe_project_manager_approved_at")
    op.drop_column("engagements", "roe_project_manager_approved_by_id")
