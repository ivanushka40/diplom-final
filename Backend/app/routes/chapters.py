from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.dependencies import CurrentUser, DbSession
from app.models import Book, Chapter, ContentBlock
from app.schemas.books import ContentRead, ContentUpdate

router = APIRouter(prefix="/chapters", tags=["chapters"])


async def owned_chapter(chapter_id: int, user_id: int, session: DbSession) -> Chapter:
    chapter = await session.scalar(
        select(Chapter).join(Book).where(Chapter.id == chapter_id, Book.owner_id == user_id)
    )
    if chapter is None:
        raise HTTPException(status_code=404, detail="Chapter not found")
    return chapter


@router.get("/{chapter_id}/content", response_model=ContentRead)
async def get_content(chapter_id: int, user: CurrentUser, session: DbSession):
    await owned_chapter(chapter_id, user.id, session)
    text = await session.scalar(
        select(ContentBlock.markdown_text).where(ContentBlock.chapter_id == chapter_id)
    )
    return {"markdown_text": text or ""}


@router.put("/{chapter_id}/content")
async def update_content(chapter_id: int, payload: ContentUpdate, user: CurrentUser, session: DbSession):
    await owned_chapter(chapter_id, user.id, session)
    block = await session.scalar(select(ContentBlock).where(ContentBlock.chapter_id == chapter_id))
    if block is None:
        session.add(ContentBlock(chapter_id=chapter_id, markdown_text=payload.markdown_text))
    else:
        block.markdown_text = payload.markdown_text
    await session.commit()
    return {"detail": "OK"}
