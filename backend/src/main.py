from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from src.composition_root import bootstrap
from src.modules.auth.interface.router import router as auth_router
from src.modules.market_data.interface.router import router as market_data_router
from src.modules.settings.interface.router import router as settings_router
from src.shared.infrastructure.cache import redis_client
from src.shared.infrastructure.database import engine
from src.shared.kernel.errors import AppError

health_router = APIRouter()


@health_router.get("/health")
def health() -> dict:
    database = "ok"
    cache = "ok"

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:
        database = "error"

    try:
        redis_client.ping()
    except Exception:
        cache = "error"

    status = "ok" if database == "ok" and cache == "ok" else "degraded"
    return {"status": status, "database": database, "cache": cache}


@asynccontextmanager
async def lifespan(app: FastAPI):
    bootstrap()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="IndraQuant API", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(AppError)
    def handle_app_error(request: Request, error: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=error.http_status,
            content={"error": {"code": error.code, "message": error.message}},
        )

    @app.exception_handler(RequestValidationError)
    def handle_validation_error(
        request: Request, error: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"error": {"code": "validation_error", "message": str(error)}},
        )

    app.include_router(health_router, prefix="/api/v1")
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(settings_router, prefix="/api/v1")
    app.include_router(market_data_router, prefix="/api/v1")
    return app


app = create_app()
