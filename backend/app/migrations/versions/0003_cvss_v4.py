"""Add versioned CVSS fields while preserving every existing v3.1 assessment.

Revision ID: 0003
Revises: 0002
"""
import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("findings") as batch:
        batch.alter_column("cvss_vector", existing_type=sa.String(80), type_=sa.String(512), existing_nullable=False)
        batch.add_column(sa.Column("cvss_version", sa.String(8), nullable=False, server_default="3.1"))
        batch.add_column(sa.Column("cvss_legacy_vector", sa.String(512), nullable=True))
        batch.add_column(sa.Column("cvss_legacy_score", sa.Float(), nullable=True))
        batch.add_column(sa.Column("cvss_legacy_severity", sa.String(12), nullable=True))
        batch.add_column(sa.Column("cvss_legacy_version", sa.String(8), nullable=True))
    with op.batch_alter_table("finding_templates") as batch:
        batch.alter_column("cvss_vector", existing_type=sa.String(80), type_=sa.String(512), existing_nullable=False)
        batch.add_column(sa.Column("cvss_version", sa.String(8), nullable=False, server_default="3.1"))


def downgrade() -> None:
    with op.batch_alter_table("finding_templates") as batch:
        batch.drop_column("cvss_version")
        batch.alter_column("cvss_vector", existing_type=sa.String(512), type_=sa.String(80), existing_nullable=False)
    with op.batch_alter_table("findings") as batch:
        batch.drop_column("cvss_legacy_version")
        batch.drop_column("cvss_legacy_severity")
        batch.drop_column("cvss_legacy_score")
        batch.drop_column("cvss_legacy_vector")
        batch.drop_column("cvss_version")
        batch.alter_column("cvss_vector", existing_type=sa.String(512), type_=sa.String(80), existing_nullable=False)
