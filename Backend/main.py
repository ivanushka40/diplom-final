from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routes import auth, books, chapters, documents, health


def create_app() -> FastAPI:
    application = FastAPI(title=settings.app_name, version="1.1.0", root_path=settings.root_path)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(health.router)
    application.include_router(auth.router)
    application.include_router(books.router)
    application.include_router(chapters.router)
    application.include_router(documents.router)
    return application


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
