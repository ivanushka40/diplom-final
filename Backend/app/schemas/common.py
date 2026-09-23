from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, StringConstraints


def normalize_username(value: object) -> object:
    return value.strip().lower() if isinstance(value, str) else value


Username = Annotated[
    str,
    StringConstraints(min_length=3, max_length=50, pattern=r"^[a-z0-9_.-]+$"),
    BeforeValidator(normalize_username),
]


class RequestSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class MessageResponse(ResponseSchema):
    detail: str


class ValidationIssue(ResponseSchema):
    loc: tuple[str | int, ...]
    msg: str
    type: str


class ValidationErrorResponse(ResponseSchema):
    detail: list[ValidationIssue]


class HealthResponse(ResponseSchema):
    status: Literal["ok"] = "ok"
