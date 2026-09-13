from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select

from app.dependencies import CurrentUser, DbSession
from app.models import User
from app.schemas.auth import AuthResponse, Credentials, Token, UserRead
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(tags=["auth"])


def response_for(user: User) -> dict:
    return {
        "access_token": create_access_token(user.id),
        "token_type": "bearer",
        "user": {"id": user.id, "username": user.username},
    }


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(credentials: Credentials, session: DbSession):
    if await session.scalar(select(User).where(User.username == credentials.username)):
        raise HTTPException(status_code=400, detail="Username already registered")
    user = User(username=credentials.username, hashed_password=hash_password(credentials.password))
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return response_for(user)


@router.post("/login", response_model=AuthResponse)
async def login_json(credentials: Credentials, session: DbSession):
    user = await session.scalar(select(User).where(User.username == credentials.username))
    if user is None or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    return response_for(user)


@router.post("/token", response_model=Token)
async def login_form(form: Annotated[OAuth2PasswordRequestForm, Depends()], session: DbSession):
    user = await session.scalar(select(User).where(User.username == form.username.strip().lower()))
    if user is None or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    return {"access_token": create_access_token(user.id), "token_type": "bearer"}


@router.get("/me", response_model=UserRead)
async def me(user: CurrentUser):
    return user
