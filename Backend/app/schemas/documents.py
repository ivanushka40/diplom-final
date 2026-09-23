from typing import TYPE_CHECKING, Annotated, Literal

from pydantic import PositiveInt, StringConstraints

from app.schemas.common import RequestSchema, ResponseSchema, Username

if TYPE_CHECKING:
    from app.models import Document

DocumentTitle = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


class DocumentCreate(RequestSchema):
    title: DocumentTitle


class DocumentRead(ResponseSchema):
    id: PositiveInt
    title: str
    is_owner: bool

    @classmethod
    def from_document(cls, document: "Document", user_id: int) -> "DocumentRead":
        return cls(id=document.id, title=document.title, is_owner=document.owner_id == user_id)


class ContentUpdate(RequestSchema):
    markdown_text: str


class ContentRead(ResponseSchema):
    markdown_text: str


class MemberCreate(RequestSchema):
    username: Username


class MemberRead(ResponseSchema):
    # id stays the user ID for the existing UI; membership_id is the relation's PK.
    id: PositiveInt
    username: str
    role: Literal["owner", "editor"]
    membership_id: PositiveInt | None = None
