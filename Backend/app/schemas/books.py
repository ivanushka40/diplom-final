from pydantic import BaseModel, ConfigDict, Field


class BookCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)


class BookRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    description: str | None = None


class ChapterCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    parent_id: int | None = None
    order_num: int = 0


class ChapterRead(BaseModel):
    id: int
    title: str
    order_num: int
    children: list["ChapterRead"] = Field(default_factory=list)


class ContentUpdate(BaseModel):
    markdown_text: str


class ContentRead(ContentUpdate):
    pass
