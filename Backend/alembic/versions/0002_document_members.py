"""Add per-document collaborators."""
from alembic import op
import sqlalchemy as sa

revision = "0002_document_members"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "document_members",
        sa.Column("chapter_id", sa.Integer(), sa.ForeignKey("chapters.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    )


def downgrade() -> None:
    op.drop_table("document_members")
