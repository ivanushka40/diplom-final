from fastapi import FastAPI, HTTPException, Depends, status, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from datetime import datetime, timedelta
import jwt
import base64
import hashlib
import hmac
import os
from pathlib import Path
from uvicorn import run

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import select, or_, ForeignKey

# --- Настройки ---
SECRET_KEY = "your-secret-key-change-in-prod"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

DATABASE_URL = "postgresql+asyncpg://postgres:postgres@127.0.0.1/postgres"
engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

app = FastAPI(title="Nota API", version="1.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
PROJECT_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIST = PROJECT_DIR / "Frontend" / "dist"


class Base(DeclarativeBase):
    pass


# --- Модели БД ---
class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(unique=True, index=True)
    hashed_password: Mapped[str]

    books: Mapped[List["Book"]] = relationship(back_populates="owner")


class Book(Base):
    __tablename__ = "books"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(index=True)
    description: Mapped[Optional[str]]
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    owner: Mapped[User] = relationship(back_populates="books")
    chapters: Mapped[List["Chapter"]] = relationship(back_populates="book", order_by="Chapter.order_num")


class Chapter(Base):
    __tablename__ = "chapters"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str]
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id"))
    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("chapters.id"))  # Для вложенности
    order_num: Mapped[int] = mapped_column(default=0)  # Порядок сортировки

    book: Mapped[Book] = relationship(back_populates="chapters")
    content: Mapped[Optional["ContentBlock"]] = relationship(uselist=False, back_populates="chapter")
    children: Mapped[List["Chapter"]] = relationship(order_by=order_num)


class ContentBlock(Base):
    __tablename__ = "content_blocks"
    id: Mapped[int] = mapped_column(primary_key=True)
    chapter_id: Mapped[int] = mapped_column(ForeignKey("chapters.id"), unique=True)
    markdown_text: Mapped[str]

    chapter: Mapped[Chapter] = relationship(back_populates="content")


# --- Pydantic схемы (DTO) ---
class Token(BaseModel):
    access_token: str
    token_type: str


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(min_length=8, max_length=128)

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        return value.strip().lower()


class Credentials(UserCreate):
    pass


class UserRead(BaseModel):
    id: int
    username: str

    class Config:
        from_attributes = True


class BookRead(BaseModel):
    id: int
    title: str
    description: Optional[str] = None

    class Config:
        from_attributes = True


class BookCreate(BaseModel):
    title: str
    description: Optional[str] = None


class ChapterCreate(BaseModel):
    title: str
    parent_id: Optional[int] = None
    order_num: int = 0


class ChapterRead(BaseModel):
    id: int
    title: str
    order_num: int
    children: List['ChapterRead'] = []

    class Config:
        from_attributes = True


class ContentUpdate(BaseModel):
    markdown_text: str


# --- Утилиты безопасности ---
def verify_password(plain_password, hashed_password):
    try:
        algorithm, iterations, salt, digest = hashed_password.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        candidate = hashlib.pbkdf2_hmac("sha256", plain_password.encode(), base64.urlsafe_b64decode(salt), int(iterations))
        return hmac.compare_digest(base64.urlsafe_b64encode(candidate).decode(), digest)
    except (ValueError, TypeError):
        return False


def get_password_hash(password):
    salt = os.urandom(16)
    iterations = 310_000
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    return "pbkdf2_sha256${}${}${}".format(iterations, base64.urlsafe_b64encode(salt).decode(), base64.urlsafe_b64encode(digest).decode())


def create_access_token(user_id: int) -> str:
    expires_at = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": str(user_id), "exp": expires_at}, SECRET_KEY, algorithm=ALGORITHM)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = int(payload.get("sub"))
        if user_id is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    return user


# --- Роуты ---
@app.post("/register", status_code=status.HTTP_201_CREATED)
async def register(user: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == user.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already registered")

    new_user = User(username=user.username, hashed_password=get_password_hash(user.password))
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return {"access_token": create_access_token(new_user.id), "token_type": "bearer", "user": {"id": new_user.id, "username": new_user.username}}


@app.post("/login")
async def login_json(credentials: Credentials, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == credentials.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверное имя пользователя или пароль")
    return {"access_token": create_access_token(user.id), "token_type": "bearer", "user": {"id": user.id, "username": user.username}}


@app.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == form_data.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(user.id)
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/me", response_model=UserRead)
async def read_current_user(current_user: User = Depends(get_current_user)):
    return current_user


@app.post("/books/")
async def create_book(book: BookCreate, current_user: User = Depends(get_current_user),
                      db: AsyncSession = Depends(get_db)):
    db_book = Book(title=book.title, description=book.description, owner_id=current_user.id)
    db.add(db_book)
    await db.commit()
    await db.refresh(db_book)
    return db_book


@app.get("/books/", response_model=List[BookRead])
async def read_books(
                     skip: int = Query(0, ge=0),
                     limit: int = Query(50, ge=1, le=100),
                     q: Optional[str] = Query(None, min_length=1, max_length=100),
                     current_user: User = Depends(get_current_user),
                     db: AsyncSession = Depends(get_db)):
    """Возвращает только книги текущего пользователя; q ищет по названию и описанию."""
    stmt = select(Book).where(Book.owner_id == current_user.id)
    if q:
        pattern = f"%{q.strip()}%"
        stmt = stmt.where(or_(Book.title.ilike(pattern), Book.description.ilike(pattern)))
    result = await db.execute(stmt.order_by(Book.title).offset(skip).limit(limit))
    return result.scalars().all()



@app.post("/books/{book_id}/chapters/")
async def create_chapter(book_id: int, chapter: ChapterCreate, current_user: User = Depends(get_current_user),
                         db: AsyncSession = Depends(get_db)):
    # Проверка прав владельца
    result = await db.execute(select(Book).where(Book.id == book_id, Book.owner_id == current_user.id))
    book = result.scalar_one_or_none()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    db_chapter = Chapter(title=chapter.title, book_id=book_id, parent_id=chapter.parent_id, order_num=chapter.order_num)
    db.add(db_chapter)
    await db.commit()
    await db.refresh(db_chapter)
    return db_chapter


@app.get("/books/{book_id}/tree", response_model=List[ChapterRead])
async def get_book_tree(book_id: int,
                        q: Optional[str] = Query(None, min_length=1, max_length=100),
                        current_user: User = Depends(get_current_user),
                        db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Book).where(Book.id == book_id, Book.owner_id == current_user.id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404)

    result = await db.execute(select(Chapter).where(Chapter.book_id == book_id).order_by(Chapter.order_num))
    chapters = result.scalars().all()
    chapters_by_parent = {}
    for chapter in chapters:
        chapters_by_parent.setdefault(chapter.parent_id, []).append(chapter)

    matching_ids = None
    if q:
        pattern = f"%{q.strip()}%"
        matching = await db.execute(
            select(Chapter.id).where(Chapter.book_id == book_id, Chapter.title.ilike(pattern))
        )
        matching_ids = set(matching.scalars().all())
        # Keep every ancestor of a matched chapter so the filtered tree remains navigable.
        by_id = {chapter.id: chapter for chapter in chapters}
        for chapter_id in list(matching_ids):
            parent_id = by_id[chapter_id].parent_id
            while parent_id is not None:
                matching_ids.add(parent_id)
                parent_id = by_id[parent_id].parent_id

    def build_tree(chapter):
        data = {
            "id": chapter.id,
            "title": chapter.title,
            "order_num": chapter.order_num,
            "children": []
        }
        for child in chapters_by_parent.get(chapter.id, []):
            if matching_ids is None or child.id in matching_ids:
                data["children"].append(build_tree(child))
        return data

    return [build_tree(root) for root in chapters_by_parent.get(None, [])
            if matching_ids is None or root.id in matching_ids]


@app.get("/chapters/{chapter_id}/content")
async def get_content(chapter_id: int, current_user: User = Depends(get_current_user),
                      db: AsyncSession = Depends(get_db)):
    stmt = (
        select(ContentBlock.markdown_text)
        .join(Chapter)
        .where(ContentBlock.chapter_id == chapter_id, Chapter.book_id.in_(
            select(Book.id).where(Book.owner_id == current_user.id)
        ))
    )
    result = await db.execute(stmt)
    text = result.scalar_one_or_none()
    if text is None:
        return {"markdown_text": ""}
    return {"markdown_text": text}


@app.put("/chapters/{chapter_id}/content")
async def update_content(chapter_id: int, content: ContentUpdate, current_user: User = Depends(get_current_user),
                         db: AsyncSession = Depends(get_db)):
    # Транзакция проверяет владение книгой через связь Глава -> Книга
    result = await db.execute(
        select(ContentBlock).join(Chapter).where(
            ContentBlock.chapter_id == chapter_id,
            Chapter.book_id.in_(select(Book.id).where(Book.owner_id == current_user.id))
        )
    )
    block = result.scalar_one_or_none()
    if block:
        block.markdown_text = content.markdown_text
    else:
        # Если блока нет, создаем его (проверка владения главой уже сделана выше через join)
        new_block = ContentBlock(chapter_id=chapter_id, markdown_text=content.markdown_text)
        db.add(new_block)
    await db.commit()
    return {"detail": "OK"}


# Production mode: FastAPI serves the compiled React app and its assets.
app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets", check_dir=False), name="assets")


@app.get("/{client_path:path}", include_in_schema=False)
async def serve_frontend(client_path: str):
    index_file = FRONTEND_DIST / "index.html"
    if not index_file.is_file():
        raise HTTPException(status_code=503, detail="Frontend is not built yet")
    return FileResponse(index_file)

if __name__ == "__main__":
    run(app)
