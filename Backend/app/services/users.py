from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User
from app.schemas.auth import Credentials
from app.security import hash_password, verify_password
from app.services.errors import AuthenticationError, UserAlreadyExistsError


class UserService:
    def __init__(self, orm_session: AsyncSession):
        self.orm_session = orm_session

    async def get_user(self, user_id: int) -> User | None:
        stmt = (
            select(User)
            .where(User.id == user_id)
        )
        return await self.orm_session.scalar(stmt)

    async def get_by_username(self, username: str) -> User | None:
        stmt = (
            select(User)
            .where(User.username == username)
        )
        return await self.orm_session.scalar(stmt)

    async def register(self, payload: Credentials) -> User:
        if await self.get_by_username(payload.username) is not None:
            raise UserAlreadyExistsError("Username already registered")
        user = User(username=payload.username, hashed_password=hash_password(payload.password))
        try:
            async with self.orm_session.begin_nested():
                self.orm_session.add(user)
                await self.orm_session.flush()
        except IntegrityError:
            if await self.get_by_username(payload.username) is not None:
                raise UserAlreadyExistsError("Username already registered") from None
            raise
        await self.orm_session.refresh(user)
        return user

    async def authenticate(self, payload: Credentials) -> User:
        user = await self.get_by_username(payload.username)
        if user is None or not verify_password(payload.password, user.hashed_password):
            raise AuthenticationError("Incorrect username or password")
        return user
