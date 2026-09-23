import asyncio
import importlib.util
from pathlib import Path
import unittest

from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi import HTTPException
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session

from app.database import Base
from app.models import User
from app.routes.documents import (
    add_member, create_document, get_content, list_documents, list_members, update_content,
)
from app.schemas.documents import ContentUpdate, DocumentCreate, MemberCreate


class AsyncSessionAdapter:
    """Exercise route queries against SQLite without an async SQLite driver."""
    def __init__(self, session):
        self.session = session

    def add(self, value):
        self.session.add(value)

    async def commit(self):
        self.session.commit()

    async def refresh(self, value):
        self.session.refresh(value)

    async def rollback(self):
        self.session.rollback()

    async def scalar(self, query):
        return self.session.scalar(query)

    async def scalars(self, query):
        return self.session.scalars(query)

    async def get(self, model, key):
        return self.session.get(model, key)


class DocumentSchemaTests(unittest.TestCase):
    def test_migration_preserves_content_and_members(self):
        engine = create_engine("sqlite:///:memory:")
        with engine.begin() as connection:
            connection.execute(text("PRAGMA foreign_keys=ON"))
            operations = Operations(MigrationContext.configure(connection))
            migrations = sorted((Path(__file__).parents[1] / "alembic" / "versions").glob("*.py"))
            for path in migrations:
                spec = importlib.util.spec_from_file_location(path.stem, path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                module.op = operations
                if path.stem.startswith("0003"):
                    connection.execute(text("INSERT INTO users VALUES (1, 'owner', 'hash'), (2, 'editor', 'hash')"))
                    connection.execute(text("INSERT INTO books VALUES (1, 'Library', 'Description', 1), (2, 'Empty', NULL, 1)"))
                    connection.execute(text("INSERT INTO chapters VALUES (10, 'Parent', 1, NULL, 0), (20, 'Child', 1, 10, 1)"))
                    connection.execute(text("INSERT INTO content_blocks VALUES (1, 10, 'Existing text')"))
                    connection.execute(text("INSERT INTO document_members VALUES (10, 2)"))
                module.upgrade()
            self.assertEqual(set(inspect(connection).get_table_names()), {"users", "documents", "document_members"})
            self.assertEqual(connection.execute(text("SELECT id, title, markdown_text, owner_id FROM documents ORDER BY id")).all(), [
                (10, "Parent", "Existing text", 1), (20, "Child", "", 1),
                (21, "Library", "Description", 1), (22, "Empty", "", 1),
            ])
            self.assertEqual(connection.execute(text("SELECT * FROM document_members")).all(), [(10, 2)])
            connection.execute(text("INSERT INTO documents (title, owner_id) VALUES ('New', 1)"))
            self.assertEqual(connection.execute(text("SELECT MAX(id) FROM documents")).scalar(), 23)
            connection.execute(text("DELETE FROM documents WHERE id = 10"))
            self.assertEqual(connection.execute(text("SELECT COUNT(*) FROM document_members")).scalar(), 0)
            self.assertEqual(connection.execute(text("PRAGMA foreign_key_check")).all(), [])
        engine.dispose()

    def test_document_access(self):
        async def run():
            engine = create_engine("sqlite:///:memory:")
            Base.metadata.create_all(engine)
            self.assertEqual(set(Base.metadata.tables), {"users", "documents", "document_members"})
            with Session(engine, expire_on_commit=False) as sync:
                session = AsyncSessionAdapter(sync)
                owner, editor, outsider = [User(username=name, hashed_password="test") for name in ("owner", "editor", "outsider")]
                sync.add_all([owner, editor, outsider])
                sync.commit()
                doc = await create_document(DocumentCreate(title="Shared"), owner, session)
                private = await create_document(DocumentCreate(title="Private"), owner, session)
                async def denied(awaitable, status):
                    with self.assertRaises(HTTPException) as caught:
                        await awaitable
                    self.assertEqual(caught.exception.status_code, status)
                await denied(get_content(doc["id"], editor, session), 404)
                self.assertEqual(await list_documents(editor, session), [])
                for _ in range(2):
                    await add_member(doc["id"], MemberCreate(username="EDITOR"), owner, session)
                self.assertEqual(len(await list_members(doc["id"], owner, session)), 2)
                self.assertEqual(await list_documents(editor, session), [dict(doc, is_owner=False)])
                await update_content(doc["id"], ContentUpdate(markdown_text="Updated"), editor, session)
                self.assertEqual((await get_content(doc["id"], owner, session))["markdown_text"], "Updated")
                await denied(get_content(private["id"], editor, session), 404)
                await denied(update_content(private["id"], ContentUpdate(markdown_text="Denied"), editor, session), 404)
                await denied(add_member(doc["id"], MemberCreate(username="outsider"), editor, session), 403)
                await denied(list_members(doc["id"], outsider, session), 404)
            engine.dispose()
        asyncio.run(run())
