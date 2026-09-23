import unittest
from types import SimpleNamespace

from pydantic import ValidationError

from app.schemas.auth import Credentials, UserRead
from app.schemas.common import ValidationErrorResponse, ValidationIssue
from app.schemas.documents import ContentUpdate, DocumentCreate, MemberCreate, MemberRead
from main import create_app


class PydanticSchemaTests(unittest.TestCase):
    def test_username_normalization_is_shared(self):
        self.assertEqual(Credentials(username="  Anna.Kim  ", password="password123").username, "anna.kim")
        self.assertEqual(MemberCreate(username="  Anna.Kim  ").username, "anna.kim")
        for value in ("  ", "ab", "name@domain", "a" * 51, 123):
            with self.assertRaises(ValidationError):
                MemberCreate(username=value)

    def test_document_validation(self):
        self.assertEqual(DocumentCreate(title="  Notes  ").title, "Notes")
        for value in ("   ", "x" * 201, 123):
            with self.assertRaises(ValidationError):
                DocumentCreate(title=value)
        with self.assertRaises(ValidationError):
            DocumentCreate(title="Valid", owner_id=99)
        text = "  # Title\n\nText  "
        self.assertEqual(ContentUpdate(markdown_text=text).markdown_text, text)
        with self.assertRaises(ValidationError):
            ContentUpdate(markdown_text=None)

    def test_serialization_does_not_leak_passwords(self):
        user = SimpleNamespace(id=1, username="user", hashed_password="private")
        self.assertEqual(UserRead.model_validate(user).model_dump(), {"id": 1, "username": "user"})
        with self.assertRaises(ValidationError):
            MemberRead(id=1, username="user", role="admin")
        response = ValidationErrorResponse(detail=[ValidationIssue.model_validate({
            "loc": ("body", "password"), "msg": "Too short", "type": "string_too_short", "input": "secret",
        })])
        self.assertNotIn("secret", response.model_dump_json())

    def test_every_success_response_has_schema(self):
        app = create_app()
        for route in app.routes:
            if hasattr(route, "response_model"):
                self.assertIsNotNone(route.response_model, route.path)
        schemas = app.openapi()["components"]["schemas"]
        self.assertIn("ValidationErrorResponse", schemas)
        self.assertIn("membership_id", schemas["MemberRead"]["properties"])


class ApiContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_validation_serialization_and_sharing(self):
        import json
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session
        from app.database import Base, get_session
        from test_document_schema import AsyncSessionAdapter

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        app = create_app()

        async def session_override():
            with Session(engine, expire_on_commit=False) as session:
                yield AsyncSessionAdapter(session)

        app.dependency_overrides[get_session] = session_override

        async def request(method, path, payload=None, token=None, form=False):
            from urllib.parse import urlencode
            body = (urlencode(payload) if form else json.dumps(payload)).encode() if payload is not None else b""
            headers = [(b"content-type", b"application/x-www-form-urlencoded" if form else b"application/json")]
            if token:
                headers.append((b"authorization", ("Bearer " + token).encode()))
            messages = []
            async def receive():
                return {"type": "http.request", "body": body, "more_body": False}
            async def send(message):
                messages.append(message)
            await app({
                "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
                "method": method, "scheme": "http", "path": path, "raw_path": path.encode(),
                "query_string": b"", "headers": headers, "client": ("test", 123), "server": ("test", 80),
            }, receive, send)
            return messages[0]["status"], json.loads(b"".join(m.get("body", b"") for m in messages[1:]))

        try:
            tokens = []
            for name in ("Owner", "Editor", "Outsider"):
                status, data = await request("POST", "/register", {"username": name, "password": "password123"})
                self.assertEqual(status, 201)
                self.assertEqual(set(data["user"]), {"id", "username"})
                tokens.append(data["access_token"])
            owner, editor, outsider = tokens
            self.assertEqual((await request("POST", "/register", {"username": " OWNER ", "password": "password123"}))[0], 400)
            self.assertEqual((await request("POST", "/login", {"username": " owner ", "password": "password123"}))[0], 200)
            self.assertEqual((await request("POST", "/login", {"username": "owner", "password": "incorrect-password"}))[0], 401)
            status, data = await request("POST", "/token", {"username": "owner", "password": "s3cr3t"}, form=True)
            self.assertEqual(status, 422)
            self.assertNotIn("s3cr3t", json.dumps(data))
            self.assertEqual((await request("POST", "/token", {"username": "owner", "password": "password123"}, form=True))[0], 200)
            for payload in ({"title": "   "}, {"title": "Valid", "owner_id": 9}):
                self.assertEqual((await request("POST", "/documents/", payload, owner))[0], 422)
            status, document = await request("POST", "/documents/", {"title": "  Notes  "}, owner)
            self.assertEqual(status, 201)
            self.assertEqual(document["title"], "Notes")
            path = f"/documents/{document['id']}"
            self.assertEqual((await request("GET", "/documents/0/content", token=owner))[0], 422)
            self.assertEqual((await request("GET", path + "/content", token=editor))[0], 404)
            for _ in range(2):
                self.assertEqual((await request("POST", path + "/members", {"username": " EDITOR "}, owner))[0], 200)
            status, members = await request("GET", path + "/members", token=owner)
            self.assertEqual(status, 200)
            self.assertEqual(len(members), 2)
            self.assertIsNone(members[0]["membership_id"])
            self.assertGreater(members[1]["membership_id"], 0)
            self.assertEqual((await request("PUT", path + "/content", {"markdown_text": "  saved\n"}, editor))[0], 200)
            self.assertEqual((await request("GET", path + "/content", token=owner))[1], {"markdown_text": "  saved\n"})
            self.assertEqual((await request("POST", path + "/members", {"username": "outsider"}, editor))[0], 403)
            self.assertEqual((await request("GET", path + "/members", token=outsider))[0], 404)
            self.assertEqual((await request("GET", "/documents/"))[0], 401)
        finally:
            engine.dispose()
