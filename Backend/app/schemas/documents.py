from pydantic import BaseModel, Field


class DocumentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)


class DocumentRead(BaseModel):
    id: int
    title: str
    is_owner: bool


class ContentUpdate(BaseModel):
    markdown_text: str


class MemberCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)


class MemberRead(BaseModel):
    id: int
    username: str
    role: str
