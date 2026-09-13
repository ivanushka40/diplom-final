"""Initial Nota schema."""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("users", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("username", sa.String(), nullable=False), sa.Column("hashed_password", sa.String(), nullable=False), sa.UniqueConstraint("username"))
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    op.create_table("books", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("title", sa.String(), nullable=False), sa.Column("description", sa.String(), nullable=True), sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False))
    op.create_index("ix_books_title", "books", ["title"])
    op.create_table("chapters", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("title", sa.String(), nullable=False), sa.Column("book_id", sa.Integer(), sa.ForeignKey("books.id", ondelete="CASCADE"), nullable=False), sa.Column("parent_id", sa.Integer(), sa.ForeignKey("chapters.id", ondelete="CASCADE"), nullable=True), sa.Column("order_num", sa.Integer(), nullable=False, server_default="0"))
    op.create_table("content_blocks", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("chapter_id", sa.Integer(), sa.ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False, unique=True), sa.Column("markdown_text", sa.Text(), nullable=False))


def downgrade() -> None:
    op.drop_table("content_blocks")
    op.drop_table("chapters")
    op.drop_index("ix_books_title", table_name="books")
    op.drop_table("books")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")
