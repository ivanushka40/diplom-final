from typing import Annotated

from fastapi import APIRouter, Path

from app.dependencies import CurrentUser, DbSession
from app.schemas.common import MessageResponse
from app.schemas.documents import (
    ContentRead, ContentUpdate, DocumentCreate, DocumentRead, MemberCreate, MemberRead,
)
from app.services.documents import DocumentService

router = APIRouter(prefix="/documents", tags=["documents"])
DocumentId = Annotated[int, Path(gt=0)]


@router.get("/", response_model=list[DocumentRead])
async def list_documents(user: CurrentUser, session: DbSession) -> list[DocumentRead]:
    documents = await DocumentService(session).list_documents(user.id)
    return [DocumentRead.from_document(document, user.id) for document in documents]


@router.post("/", response_model=DocumentRead, status_code=201)
async def create_document(
    payload: DocumentCreate, user: CurrentUser, session: DbSession
) -> DocumentRead:
    document = await DocumentService(session).create_document(payload, user.id)
    response = DocumentRead.from_document(document, user.id)
    await session.commit()
    return response


@router.get("/{document_id}/content", response_model=ContentRead)
async def get_content(
    document_id: DocumentId, user: CurrentUser, session: DbSession
) -> ContentRead:
    document = await DocumentService(session).get_document(document_id, user.id)
    return ContentRead.model_validate(document)


@router.put("/{document_id}/content", response_model=MessageResponse)
async def update_content(
    document_id: DocumentId, payload: ContentUpdate, user: CurrentUser, session: DbSession
) -> MessageResponse:
    await DocumentService(session).update_content(document_id, user.id, payload)
    await session.commit()
    return MessageResponse(detail="OK")


@router.get("/{document_id}/members", response_model=list[MemberRead])
async def list_members(
    document_id: DocumentId, user: CurrentUser, session: DbSession
) -> list[MemberRead]:
    owner, members = await DocumentService(session).list_members(document_id, user.id)
    return [MemberRead(id=owner.id, username=owner.username, role="owner")] + [
        MemberRead(id=user.id, username=user.username, role="editor", membership_id=membership_id)
        for user, membership_id in members
    ]


@router.post("/{document_id}/members", response_model=MessageResponse)
async def add_member(
    document_id: DocumentId, payload: MemberCreate, user: CurrentUser, session: DbSession
) -> MessageResponse:
    await DocumentService(session).add_member(document_id, user.id, payload)
    await session.commit()
    return MessageResponse(detail="Доступ предоставлен")
