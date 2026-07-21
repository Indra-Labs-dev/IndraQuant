from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from src.composition_root import (
    alert_runner,
    bootstrap,
    paper_trading_runner,
    prediction_resolver_runner,
    resume_running_paper_sessions,
)
from src.modules.ai_assistant.interface.router import router as ai_assistant_router
from src.modules.alert_center.interface.router import router as alert_center_router
from src.modules.backtesting.interface.router import router as backtesting_router
from src.modules.auth.interface.router import router as auth_router
from src.modules.economic_calendar.interface.router import (
    router as economic_calendar_router,
)
from src.modules.market_data.interface.router import router as market_data_router
from src.modules.news_intelligence.interface.router import router as news_router
from src.modules.paper_trading.interface.router import router as paper_trading_router
from src.modules.prediction_engine.interface.router import (
    router as prediction_engine_router,
)
from src.modules.smart_money.interface.router import router as smart_money_router
from src.modules.market_data.interface.ws_router import router as market_data_ws_router
from src.modules.pattern_recognition.interface.router import (
    router as pattern_recognition_router,
)
from src.modules.settings.interface.router import router as settings_router
from src.modules.strategy_builder.interface.router import (
    router as strategy_builder_router,
)
from src.modules.technical_analysis.interface.router import (
    router as technical_analysis_router,
)
from src.shared.infrastructure.cache import redis_client
from src.shared.infrastructure.database import engine
from src.shared.kernel.errors import AppError
from src.shared.plugins.loader import discover_plugins

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
    import asyncio

    bootstrap()
    paper_trading_runner.attach_loop(asyncio.get_running_loop())
    resume_running_paper_sessions()
    alert_runner.start()
    prediction_resolver_runner.start()
    yield
    prediction_resolver_runner.stop()
    alert_runner.stop()
    paper_trading_runner.stop_all()


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
    app.include_router(market_data_ws_router, prefix="/api/v1")
    app.include_router(technical_analysis_router, prefix="/api/v1")
    app.include_router(pattern_recognition_router, prefix="/api/v1")
    app.include_router(backtesting_router, prefix="/api/v1")
    app.include_router(paper_trading_router, prefix="/api/v1")
    app.include_router(prediction_engine_router, prefix="/api/v1")
    app.include_router(smart_money_router, prefix="/api/v1")
    app.include_router(economic_calendar_router, prefix="/api/v1")
    app.include_router(news_router, prefix="/api/v1")
    app.include_router(ai_assistant_router, prefix="/api/v1")
    app.include_router(alert_center_router, prefix="/api/v1")
    app.include_router(strategy_builder_router, prefix="/api/v1")

    for plugin in discover_plugins():
        app.include_router(
            plugin.router,
            prefix=f"/api/v1/plugins/{plugin.name}",
            tags=[f"plugin:{plugin.name}"],
        )
    return app


app = create_app()
