from sqlalchemy import or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Document, DocumentMember, User
from app.schemas.documents import ContentUpdate, DocumentCreate, MemberCreate
from app.services.errors import ForbiddenError, NotFoundError
from app.services.users import UserService


class DocumentService:
    def __init__(self, orm_session: AsyncSession):
        self.orm_session = orm_session

    def visible_to(self, user_id: int):
        memberships = (
            select(DocumentMember.document_id)
            .where(DocumentMember.user_id == user_id)
        )
        return or_(Document.owner_id == user_id, Document.id.in_(memberships))

    async def get_document(self, document_id: int, user_id: int) -> Document:
        stmt = (
            select(Document)
            .where(Document.id == document_id)
            .where(self.visible_to(user_id))
        )
        document = await self.orm_session.scalar(stmt)
        if document is None:
            raise NotFoundError("Документ не найден")
        return document

    async def list_documents(self, user_id: int) -> list[Document]:
        stmt = (
            select(Document)
            .where(self.visible_to(user_id))
            .order_by(Document.title, Document.id)
        )
        return list(await self.orm_session.scalars(stmt))

    async def create_document(self, payload: DocumentCreate, owner_id: int) -> Document:
        document = Document(**payload.model_dump(), owner_id=owner_id)
        self.orm_session.add(document)
        await self.orm_session.flush()
        await self.orm_session.refresh(document)
        return document

    async def update_content(self, document_id: int, user_id: int, payload: ContentUpdate) -> None:
        await self.get_document(document_id, user_id)
        stmt = (
            update(Document)
            .where(Document.id == document_id)
            .where(self.visible_to(user_id))
            .values(**payload.model_dump())
        )
        await self.orm_session.execute(stmt)

    async def list_members(
        self, document_id: int, user_id: int
    ) -> tuple[User, list[tuple[User, int]]]:
        document = await self.get_document(document_id, user_id)
        owner = await UserService(self.orm_session).get_user(document.owner_id)
        stmt = (
            select(User, DocumentMember.id.label("membership_id"))
            .join(DocumentMember, DocumentMember.user_id == User.id)
            .where(DocumentMember.document_id == document_id)
            .order_by(User.username)
        )
        members = (await self.orm_session.execute(stmt)).all()
        return owner, [(user, membership_id) for user, membership_id in members]

    async def get_membership(self, document_id: int, user_id: int) -> DocumentMember | None:
        stmt = (
            select(DocumentMember)
            .where(DocumentMember.document_id == document_id)
            .where(DocumentMember.user_id == user_id)
        )
        return await self.orm_session.scalar(stmt)

    async def add_member(self, document_id: int, owner_id: int, payload: MemberCreate) -> None:
        document = await self.get_document(document_id, owner_id)
        if document.owner_id != owner_id:
            raise ForbiddenError("Только владелец может добавлять участников")
        member = await UserService(self.orm_session).get_by_username(payload.username)
        if member is None:
            raise NotFoundError("Пользователь не найден. Сначала ему нужно зарегистрироваться")
        member_id = member.id
        if member_id == owner_id or await self.get_membership(document_id, member_id) is not None:
            return
        try:
            async with self.orm_session.begin_nested():
                self.orm_session.add(DocumentMember(document_id=document_id, user_id=member_id))
                await self.orm_session.flush()
        except IntegrityError:
            if await self.get_membership(document_id, member_id) is None:
                raise
