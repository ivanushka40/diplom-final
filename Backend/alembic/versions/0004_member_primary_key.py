"""Give document memberships a surrogate primary key."""
from alembic import op
import sqlalchemy as sa

revision = "0004_member_primary_key"
down_revision = "0003_documents_only"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "document_members_new",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.UniqueConstraint("document_id", "user_id", name="uq_document_members_document_user"),
    )
    op.execute(sa.text("""
        INSERT INTO document_members_new (document_id, user_id)
        SELECT document_id, user_id FROM document_members ORDER BY document_id, user_id
    """))
    op.drop_table("document_members")
    op.rename_table("document_members_new", "document_members")
    op.create_index("ix_document_members_user_id", "document_members", ["user_id"])


def downgrade() -> None:
    op.create_table(
        "document_members_old",
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    )
    op.execute(sa.text("""
        INSERT INTO document_members_old (document_id, user_id)
        SELECT document_id, user_id FROM document_members
    """))
    op.drop_table("document_members")
    op.rename_table("document_members_old", "document_members")
    op.create_index("ix_document_members_user_id", "document_members", ["user_id"])
