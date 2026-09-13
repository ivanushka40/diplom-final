# Nota

Структура проекта повторяет инфраструктурный подход reference backend, при этом backend полностью изолирован в `Backend/`, как и frontend в `Frontend/`.

```text
.
├── Backend/            # FastAPI, модели, роуты, схемы, Alembic, тесты, uv
├── Frontend/           # React/Vite и собственный Dockerfile
├── nginx/              # единая точка входа и прокси /api → backend
├── compose.yaml        # PostgreSQL, миграции, backend, frontend, gateway
└── .env.example
```

## Запуск всего проекта

```bash
docker compose up --build
```

После запуска интерфейс доступен на `http://localhost:5173`, Swagger — на `http://localhost:5173/api/docs`, прямой API — на `http://localhost:8000`.

## Локальная разработка

Backend:

```bash
cd Backend
uv sync
uv run alembic upgrade head
uv run uvicorn main:app --reload
```

Frontend:

```bash
cd Frontend
npm ci
npm run dev
```
