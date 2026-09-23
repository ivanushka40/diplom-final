"""Flatten the library into documents, preserving text, owners and members."""
from alembic import op
import sqlalchemy as sa

revision = "0003_documents_only"
down_revision = "0002_document_members"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("markdown_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    )
    op.create_index("ix_documents_title", "documents", ["title"])
    op.create_index("ix_documents_owner_id", "documents", ["owner_id"])
    op.execute(sa.text("""
        INSERT INTO documents (id, title, markdown_text, owner_id)
        SELECT c.id, c.title, COALESCE(t.markdown_text, ''), b.owner_id
        FROM chapters c JOIN books b ON b.id = c.book_id
        LEFT JOIN content_blocks t ON t.chapter_id = c.id
    """))
    # Keep empty books and descriptions as separate documents instead of discarding them.
    op.execute(sa.text("""
        INSERT INTO documents (id, title, markdown_text, owner_id)
        SELECT (SELECT COALESCE(MAX(id), 0) FROM chapters) + ROW_NUMBER() OVER (ORDER BY b.id),
               b.title, COALESCE(b.description, ''), b.owner_id
        FROM books b
        WHERE COALESCE(b.description, '') <> ''
           OR NOT EXISTS (SELECT 1 FROM chapters c WHERE c.book_id = b.id)
    """))
    op.create_table(
        "document_members_new",
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    )
    op.execute(sa.text("""
        INSERT INTO document_members_new (document_id, user_id)
        SELECT chapter_id, user_id FROM document_members
    """))
    op.drop_table("document_members")
    op.rename_table("document_members_new", "document_members")
    op.create_index("ix_document_members_user_id", "document_members", ["user_id"])
    op.drop_table("content_blocks")
    # Clear only the obsolete hierarchy so SQLite also permits dropping self-referencing rows.
    op.execute(sa.text("UPDATE chapters SET parent_id = NULL"))
    op.drop_table("chapters")
    op.drop_index("ix_books_title", table_name="books")
    op.drop_table("books")
    if op.get_context().dialect.name == "postgresql":
        op.execute(sa.text("""
            SELECT setval(pg_get_serial_sequence('documents', 'id'),
                          COALESCE(MAX(id), 1), MAX(id) IS NOT NULL)
            FROM documents
        """))


def downgrade() -> None:
    raise RuntimeError(
        "The former book/chapter hierarchy cannot be reconstructed. "
        "Restore a backup to return to revision 0002_document_members."
    )
