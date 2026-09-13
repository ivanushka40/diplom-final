# Nota Backend

Backend изолирован в этой директории. Команды выполняются из `Backend/`.

```bash
uv sync
uv run alembic upgrade head
uv run uvicorn main:app --reload
uv run pytest
```

API: `http://localhost:8000`, Swagger: `http://localhost:8000/docs`.
