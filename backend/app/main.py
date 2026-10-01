import logging
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.admin import router as admin_router
from app.api.v1.business import router as business_router
from app.api.v1.confirmation import router as confirmation_router
from app.api.v1.health import router as health_router
from app.api.v1.ocr import router as ocr_router
from app.api.v1.profile_metrics import router as profile_metrics_router
from app.api.v1.reports import router as reports_router
from app.confirmation import ConfirmationError
from app.core.config import get_settings
from app.core.logging import configure_logging

settings = get_settings()
configure_logging(settings.log_level)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("qcloud_cos").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

app = FastAPI(title="Checkup API")
app.include_router(health_router, prefix="/api/v1")
app.include_router(business_router, prefix="/api/v1")
app.include_router(ocr_router, prefix="/api/v1")
app.include_router(confirmation_router, prefix="/api/v1")
app.include_router(reports_router, prefix="/api/v1")
app.include_router(profile_metrics_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")


@app.exception_handler(RequestValidationError)
async def invalid_input(request: Request, exc: RequestValidationError):
    from fastapi.exception_handlers import request_validation_exception_handler
    if request.url.path.startswith("/api/v1/admin/"):
        return JSONResponse(status_code=422, content={
            "code": "INVALID_ADMIN_INPUT", "message": "INVALID_ADMIN_INPUT",
            "request_id": request.state.request_id, "details": {},
        })
    return await request_validation_exception_handler(request, exc)


@app.exception_handler(ConfirmationError)
async def confirmation_error(request: Request, exc: ConfirmationError) -> JSONResponse:
    return JSONResponse(status_code=exc.status, content=jsonable_encoder({
        "code": exc.code, "message": exc.code,
        "request_id": request.state.request_id, "details": exc.details,
    }))


@app.exception_handler(StarletteHTTPException)
async def http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    code = (str(exc.detail) if isinstance(exc.detail, str) and exc.detail.isupper()
            else "NOT_FOUND" if exc.status_code == 404 else "HTTP_ERROR")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": code,
            "message": str(exc.detail),
            "request_id": request.state.request_id,
            "details": {},
        },
    )


@app.middleware("http")
async def request_logging(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid4())
    request.state.request_id = request_id
    started = perf_counter()
    try:
        response = await call_next(request)
    except Exception:  # noqa: BLE001 - do not expose SQL bound medical values
        # SQLAlchemy exception strings can include bound medical values. Keep
        # ordinary request logs to identifiers and stable codes only.
        logger.error("request_id=%s path=%s error_code=INTERNAL_ERROR", request_id, request.url.path)
        response = JSONResponse(
            status_code=500,
            content={"code": "INTERNAL_ERROR", "message": "Internal server error", "request_id": request_id, "details": {}},
        )
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "request_id=%s path=%s status=%s duration_ms=%.1f",
        request_id,
        request.url.path,
        response.status_code,
        (perf_counter() - started) * 1000,
    )
    return response
