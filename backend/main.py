import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from api.routes import api_router
from core.config import get_settings
from core.logging import configure_logging, request_id_var
from core.middleware import RequestContextMiddleware
from core.rate_limit import limiter
from core.scheduler import start_scheduler, stop_scheduler

configure_logging()
logger = logging.getLogger("applytics")


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    stop_scheduler()


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(title="Applytics API", version="0.1.0", lifespan=lifespan)

    app.state.limiter = limiter

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
        return JSONResponse(status_code=429, content={"detail": f"Rate limit exceeded: {exc.detail}"})

    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "request_id": request_id_var.get()},
        )

    app.include_router(api_router, prefix=settings.api_v1_prefix)

    return app


app = create_app()
