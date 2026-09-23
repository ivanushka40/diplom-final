from fastapi import APIRouter, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError

from app.dependencies import CurrentUser, DbSession
from app.models import Document, DocumentMember, User
from app.schemas.documents import (
    ContentUpdate, DocumentCreate, DocumentRead, MemberCreate, MemberRead,
)

router = APIRouter(prefix="/documents", tags=["documents"])


def visible_to(user_id: int):
    return or_(
        Document.owner_id == user_id,
        Document.id.in_(
            select(DocumentMember.document_id).where(DocumentMember.user_id == user_id)
        ),
    )


async def accessible_document(document_id: int, user_id: int, session: DbSession) -> Document:
    document = await session.scalar(
        select(Document).where(Document.id == document_id, visible_to(user_id))
    )
    if document is None:
        raise HTTPException(404, "Документ не найден")
    return document


@router.get("/", response_model=list[DocumentRead])
async def list_documents(user: CurrentUser, session: DbSession):
    documents = (await session.scalars(
        select(Document).where(visible_to(user.id)).order_by(Document.title, Document.id)
    )).all()
    return [
        {"id": doc.id, "title": doc.title, "is_owner": doc.owner_id == user.id}
        for doc in documents
    ]


@router.post("/", response_model=DocumentRead, status_code=201)
async def create_document(payload: DocumentCreate, user: CurrentUser, session: DbSession):
    title = payload.title.strip()
    if not title:
        raise HTTPException(422, "Укажите название документа")
    document = Document(title=title, owner_id=user.id)
    session.add(document)
    await session.commit()
    await session.refresh(document)
    return {"id": document.id, "title": document.title, "is_owner": True}


@router.get("/{document_id}/content", response_model=ContentUpdate)
async def get_content(document_id: int, user: CurrentUser, session: DbSession):
    document = await accessible_document(document_id, user.id, session)
    return {"markdown_text": document.markdown_text}


@router.put("/{document_id}/content")
async def update_content(
    document_id: int, payload: ContentUpdate, user: CurrentUser, session: DbSession
):
    document = await accessible_document(document_id, user.id, session)
    document.markdown_text = payload.markdown_text
    await session.commit()
    return {"detail": "OK"}


@router.get("/{document_id}/members", response_model=list[MemberRead])
async def list_members(document_id: int, user: CurrentUser, session: DbSession):
    document = await accessible_document(document_id, user.id, session)
    owner = await session.get(User, document.owner_id)
    members = (await session.scalars(select(User).join(DocumentMember).where(DocumentMember.document_id == document_id).order_by(User.username))).all()
    return [{"id": owner.id, "username": owner.username, "role": "owner"}] + [
        {"id": member.id, "username": member.username, "role": "editor"} for member in members
    ]


@router.post("/{document_id}/members")
async def add_member(document_id: int, payload: MemberCreate, user: CurrentUser, session: DbSession):
    document = await accessible_document(document_id, user.id, session)
    owner_id = document.owner_id
    if owner_id != user.id:
        raise HTTPException(403, "Только владелец может добавлять участников")
    member = await session.scalar(select(User).where(User.username == payload.username.strip().lower()))
    if member is None:
        raise HTTPException(404, "Пользователь не найден. Сначала ему нужно зарегистрироваться")
    member_id = member.id
    if member_id != owner_id and await session.get(DocumentMember, (document_id, member_id)) is None:
        session.add(DocumentMember(document_id=document_id, user_id=member_id))
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            if await session.get(DocumentMember, (document_id, member_id)) is None:
                raise
    return {"detail": "Доступ предоставлен"}
