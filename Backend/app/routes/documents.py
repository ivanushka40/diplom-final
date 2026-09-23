from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError

from app.dependencies import CurrentUser, DbSession
from app.models import Book, Chapter, DocumentMember, User
from app.routes.chapters import accessible_chapter

router = APIRouter(prefix="/documents", tags=["documents"])


class DocumentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)


class MemberCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)


@router.get("/")
async def list_documents(user: CurrentUser, session: DbSession):
    rows = (await session.execute(
        select(Chapter, Book.owner_id).join(Book).where(or_(
            Book.owner_id == user.id,
            Chapter.id.in_(select(DocumentMember.chapter_id).where(DocumentMember.user_id == user.id)),
        )).order_by(Chapter.title, Chapter.id)
    )).all()
    return [{"id": chapter.id, "title": chapter.title, "is_owner": owner_id == user.id} for chapter, owner_id in rows]


@router.post("/", status_code=201)
async def create_document(payload: DocumentCreate, user: CurrentUser, session: DbSession):
    title = payload.title.strip()
    if not title:
        raise HTTPException(422, "Укажите название документа")
    book = Book(title=title, owner_id=user.id)
    session.add(book)
    await session.flush()
    chapter = Chapter(title=title, book_id=book.id)
    session.add(chapter)
    await session.commit()
    await session.refresh(chapter)
    return {"id": chapter.id, "title": chapter.title, "is_owner": True}


@router.get("/{document_id}/members")
async def list_members(document_id: int, user: CurrentUser, session: DbSession):
    chapter = await accessible_chapter(document_id, user.id, session)
    owner = await session.scalar(select(User).join(Book).where(Book.id == chapter.book_id))
    members = (await session.scalars(select(User).join(DocumentMember).where(DocumentMember.chapter_id == document_id).order_by(User.username))).all()
    return [{"id": owner.id, "username": owner.username, "role": "owner"}] + [
        {"id": member.id, "username": member.username, "role": "editor"} for member in members
    ]


@router.post("/{document_id}/members")
async def add_member(document_id: int, payload: MemberCreate, user: CurrentUser, session: DbSession):
    chapter = await accessible_chapter(document_id, user.id, session)
    owner_id = await session.scalar(select(Book.owner_id).where(Book.id == chapter.book_id))
    if owner_id != user.id:
        raise HTTPException(403, "Только владелец может добавлять участников")
    member = await session.scalar(select(User).where(User.username == payload.username.strip().lower()))
    if member is None:
        raise HTTPException(404, "Пользователь не найден. Сначала ему нужно зарегистрироваться")
    member_id = member.id
    if member_id != owner_id and await session.get(DocumentMember, (document_id, member_id)) is None:
        session.add(DocumentMember(chapter_id=document_id, user_id=member_id))
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            if await session.get(DocumentMember, (document_id, member_id)) is None:
                raise
    return {"detail": "Доступ предоставлен"}
