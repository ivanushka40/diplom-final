from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.errors import http_error_handler, service_error_handler, validation_error_handler
from app.schemas.common import MessageResponse, ValidationErrorResponse
from app.services.errors import ServiceError
from app.routes import auth, documents, health


def create_app() -> FastAPI:
    application = FastAPI(
        title=settings.app_name, version="1.1.0", root_path=settings.root_path,
        responses={
            400: {"model": MessageResponse},
            401: {"model": MessageResponse},
            403: {"model": MessageResponse},
            404: {"model": MessageResponse},
            422: {"model": ValidationErrorResponse},
        },
    )
    application.add_exception_handler(ServiceError, service_error_handler)
    application.add_exception_handler(HTTPException, http_error_handler)
    application.add_exception_handler(RequestValidationError, validation_error_handler)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(health.router)
    application.include_router(auth.router)
    application.include_router(documents.router)
    return application


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
