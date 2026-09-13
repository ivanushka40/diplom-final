from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import or_, select

from app.dependencies import CurrentUser, DbSession
from app.models import Book, Chapter
from app.schemas.books import BookCreate, BookRead, ChapterCreate, ChapterRead

router = APIRouter(prefix="/books", tags=["books"])


@router.post("/", response_model=BookRead, status_code=status.HTTP_201_CREATED)
async def create_book(payload: BookCreate, user: CurrentUser, session: DbSession):
    book = Book(title=payload.title, description=payload.description, owner_id=user.id)
    session.add(book)
    await session.commit()
    await session.refresh(book)
    return book


@router.get("/", response_model=list[BookRead])
async def list_books(
    user: CurrentUser,
    session: DbSession,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    q: str | None = Query(None, min_length=1, max_length=100),
):
    query = select(Book).where(Book.owner_id == user.id)
    if q:
        pattern = f"%{q.strip()}%"
        query = query.where(or_(Book.title.ilike(pattern), Book.description.ilike(pattern)))
    result = await session.scalars(query.order_by(Book.title).offset(skip).limit(limit))
    return result.all()


async def owned_book(book_id: int, user_id: int, session: DbSession) -> Book:
    book = await session.scalar(select(Book).where(Book.id == book_id, Book.owner_id == user_id))
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


@router.post("/{book_id}/chapters/", status_code=status.HTTP_201_CREATED)
async def create_chapter(book_id: int, payload: ChapterCreate, user: CurrentUser, session: DbSession):
    await owned_book(book_id, user.id, session)
    if payload.parent_id is not None:
        parent = await session.scalar(
            select(Chapter).where(Chapter.id == payload.parent_id, Chapter.book_id == book_id)
        )
        if parent is None:
            raise HTTPException(status_code=400, detail="Parent chapter does not belong to this book")
    chapter = Chapter(book_id=book_id, **payload.model_dump())
    session.add(chapter)
    await session.commit()
    await session.refresh(chapter)
    return {"id": chapter.id, "title": chapter.title, "parent_id": chapter.parent_id, "order_num": chapter.order_num}


@router.get("/{book_id}/tree", response_model=list[ChapterRead])
async def book_tree(
    book_id: int,
    user: CurrentUser,
    session: DbSession,
    q: str | None = Query(None, min_length=1, max_length=100),
):
    await owned_book(book_id, user.id, session)
    chapters = list((await session.scalars(
        select(Chapter).where(Chapter.book_id == book_id).order_by(Chapter.order_num, Chapter.id)
    )).all())
    children: dict[int | None, list[Chapter]] = {}
    for chapter in chapters:
        children.setdefault(chapter.parent_id, []).append(chapter)
    visible = {chapter.id for chapter in chapters}
    if q:
        by_id = {chapter.id: chapter for chapter in chapters}
        visible = {chapter.id for chapter in chapters if q.casefold() in chapter.title.casefold()}
        for chapter_id in list(visible):
            parent_id = by_id[chapter_id].parent_id
            while parent_id is not None and parent_id in by_id:
                visible.add(parent_id)
                parent_id = by_id[parent_id].parent_id

    def build(chapter: Chapter) -> dict:
        return {
            "id": chapter.id,
            "title": chapter.title,
            "order_num": chapter.order_num,
            "children": [build(child) for child in children.get(chapter.id, []) if child.id in visible],
        }

    return [build(chapter) for chapter in children.get(None, []) if chapter.id in visible]
