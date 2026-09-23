from typing import Literal

from pydantic import Field, PositiveInt

from app.schemas.common import RequestSchema, ResponseSchema, Username


class Credentials(RequestSchema):
    username: Username
    password: str = Field(min_length=8, max_length=128)


class UserRead(ResponseSchema):
    id: PositiveInt
    username: str


class Token(ResponseSchema):
    access_token: str
    token_type: Literal["bearer"] = "bearer"


class AuthResponse(Token):
    user: UserRead
