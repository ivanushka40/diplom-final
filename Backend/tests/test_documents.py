import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database import Base, get_session
from main import create_app


@pytest.mark.asyncio
async def test_document_sharing_and_isolation():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    app = create_app()

    async def session_override():
        async with sessions() as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = []
        for username in ("owner", "editor", "outsider"):
            response = await client.post("/register", json={"username": username, "password": "test-password-123"})
            assert response.status_code == 201
            headers.append({"Authorization": "Bearer " + response.json()["access_token"]})
        owner, editor, outsider = headers
        response = await client.post("/documents/", headers=owner, json={"title": "Shared"})
        assert response.status_code == 201
        doc = response.json()["id"]
        other = (await client.post("/documents/", headers=owner, json={"title": "Private"})).json()["id"]
        path = f"/documents/{doc}/content"
        assert (await client.get(path, headers=editor)).status_code == 404
        assert (await client.put(path, headers=editor, json={"markdown_text": "Denied"})).status_code == 404
        assert (await client.get("/documents/", headers=editor)).json() == []
        members = f"/documents/{doc}/members"
        assert (await client.post(members, headers=outsider, json={"username": "editor"})).status_code == 404
        assert (await client.post(members, headers=owner, json={"username": "missing"})).status_code == 404
        for _ in range(2):
            assert (await client.post(members, headers=owner, json={"username": "EDITOR"})).status_code == 200
        assert len((await client.get(members, headers=owner)).json()) == 2
        assert (await client.get("/documents/", headers=editor)).json() == [{"id": doc, "title": "Shared", "is_owner": False}]
        assert (await client.put(path, headers=editor, json={"markdown_text": "Updated"})).status_code == 200
        assert (await client.get(path, headers=owner)).json()["markdown_text"] == "Updated"
        assert (await client.get(f"/documents/{other}/content", headers=editor)).status_code == 404
        assert (await client.post(members, headers=editor, json={"username": "outsider"})).status_code == 403
        assert (await client.get(members, headers=outsider)).status_code == 404
        assert (await client.get("/documents/")).status_code == 401
    await engine.dispose()
