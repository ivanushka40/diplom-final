from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.exceptions import RequestValidationError
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import ValidationError

from app.dependencies import CurrentUser, DbSession
from app.models import User
from app.schemas.auth import AuthResponse, Credentials, Token, UserRead
from app.security import create_access_token
from app.services.users import UserService

router = APIRouter(tags=["auth"])


def response_for(user: User) -> AuthResponse:
    return AuthResponse(
        access_token=create_access_token(user.id),
        user=UserRead.model_validate(user),
    )


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(credentials: Credentials, session: DbSession) -> AuthResponse:
    user = await UserService(session).register(credentials)
    response = response_for(user)
    await session.commit()
    return response


@router.post("/login", response_model=AuthResponse)
async def login_json(credentials: Credentials, session: DbSession) -> AuthResponse:
    user = await UserService(session).authenticate(credentials)
    return response_for(user)


@router.post("/token", response_model=Token)
async def login_form(
    form: Annotated[OAuth2PasswordRequestForm, Depends()], session: DbSession
) -> Token:
    try:
        credentials = Credentials(username=form.username, password=form.password)
    except ValidationError as error:
        errors = [dict(item, loc=("body", *item["loc"])) for item in error.errors()]
        raise RequestValidationError(errors) from error
    user = await UserService(session).authenticate(credentials)
    return Token(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserRead)
async def me(user: CurrentUser) -> UserRead:
    return UserRead.model_validate(user)
