from __future__ import annotations

from typing import Optional

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(unique=True, index=True)
    hashed_password: Mapped[str]
    books: Mapped[list[Book]] = relationship(back_populates="owner", cascade="all, delete-orphan")


class Book(Base):
    __tablename__ = "books"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(index=True)
    description: Mapped[Optional[str]]
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    owner: Mapped[User] = relationship(back_populates="books")
    chapters: Mapped[list[Chapter]] = relationship(
        back_populates="book", cascade="all, delete-orphan", order_by="Chapter.order_num"
    )


class Chapter(Base):
    __tablename__ = "chapters"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str]
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"))
    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("chapters.id", ondelete="CASCADE"))
    order_num: Mapped[int] = mapped_column(default=0)
    book: Mapped[Book] = relationship(back_populates="chapters")
    content: Mapped[Optional[ContentBlock]] = relationship(
        back_populates="chapter", cascade="all, delete-orphan", uselist=False
    )


class ContentBlock(Base):
    __tablename__ = "content_blocks"
    id: Mapped[int] = mapped_column(primary_key=True)
    chapter_id: Mapped[int] = mapped_column(ForeignKey("chapters.id", ondelete="CASCADE"), unique=True)
    markdown_text: Mapped[str] = mapped_column(Text)
    chapter: Mapped[Chapter] = relationship(back_populates="content")


class DocumentMember(Base):
    __tablename__ = "document_members"
    chapter_id: Mapped[int] = mapped_column(ForeignKey("chapters.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
