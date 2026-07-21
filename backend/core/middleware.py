import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from core.logging import request_id_var

logger = logging.getLogger("applytics.request")


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
        token = request_id_var.set(request_id)
        start = time.monotonic()

        try:
            response = await call_next(request)
            duration_ms = (time.monotonic() - start) * 1000
            logger.info(
                "%s %s -> %d (%.1fms)",
                request.method,
                request.url.path,
                response.status_code,
                duration_ms,
            )
            response.headers["X-Request-ID"] = request_id
            return response
        except Exception:
            logger.exception("Unhandled exception for %s %s", request.method, request.url.path)
            raise
        finally:
            request_id_var.reset(token)
