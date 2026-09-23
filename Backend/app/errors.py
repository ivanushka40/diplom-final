from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.schemas.common import MessageResponse, ValidationErrorResponse, ValidationIssue
from app.services.errors import ServiceError


async def service_error_handler(request: Request, error: ServiceError) -> JSONResponse:
    response = MessageResponse(detail=str(error))
    return JSONResponse(status_code=error.status_code, content=response.model_dump(mode="json"))


async def http_error_handler(request: Request, error: HTTPException) -> JSONResponse:
    response = MessageResponse(detail=str(error.detail))
    return JSONResponse(
        status_code=error.status_code, content=response.model_dump(mode="json"), headers=error.headers
    )


async def validation_error_handler(request: Request, error: RequestValidationError) -> JSONResponse:
    response = ValidationErrorResponse(detail=[
        ValidationIssue.model_validate(item) for item in error.errors()
    ])
    # Do not echo submitted passwords or document text in validation errors.
    return JSONResponse(status_code=422, content=response.model_dump(mode="json"))
