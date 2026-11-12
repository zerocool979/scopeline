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
    with op.batch_alter_table("engagements") as batch:
        batch.add_column(sa.Column("roe_project_manager_approved_by_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("roe_project_manager_approved_at", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("roe_head_approved_by_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("roe_head_approved_at", sa.DateTime(), nullable=True))
        batch.create_foreign_key("fk_engagements_roe_pm_approver", "users",
                                 ["roe_project_manager_approved_by_id"], ["id"])
        batch.create_foreign_key("fk_engagements_roe_head_approver", "users",
                                 ["roe_head_approved_by_id"], ["id"])
    # Approval v1 tidak membuktikan persetujuan kedua pejabat; minta persetujuan ulang.
    op.execute(sa.text(
        "UPDATE engagements SET roe_approved = 0, roe_approved_by_id = NULL, roe_approved_at = NULL"
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
    with op.batch_alter_table("engagements") as batch:
        batch.drop_constraint("fk_engagements_roe_head_approver", type_="foreignkey")
        batch.drop_constraint("fk_engagements_roe_pm_approver", type_="foreignkey")
        batch.drop_column("roe_head_approved_at")
        batch.drop_column("roe_head_approved_by_id")
        batch.drop_column("roe_project_manager_approved_at")
        batch.drop_column("roe_project_manager_approved_by_id")
