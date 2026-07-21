from fastapi import APIRouter, FastAPI
from sqlalchemy import text

from src.shared.infrastructure.cache import redis_client
from src.shared.infrastructure.database import engine

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


def create_app() -> FastAPI:
    app = FastAPI(title="IndraQuant API")
    app.include_router(health_router, prefix="/api/v1")
    return app


app = create_app()
