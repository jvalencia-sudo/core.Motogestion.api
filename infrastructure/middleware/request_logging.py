"""Middleware ASGI puro (no BaseHTTPMiddleware) que loguea una línea por request
con ruta, taller y usuario, para F0-04.

Se usa ASGI puro a propósito: BaseHTTPMiddleware corre el resto del stack (incluidas
las dependencias de FastAPI, donde resolve_tenant fija taller/usuario en sus
ContextVar) en una task separada en algunas versiones de Starlette, y no hay
garantía de que esos ContextVar se sigan viendo después del `call_next` en el código
de la propia clase de middleware. Con ASGI puro no hay ese riesgo: todo corre en la
misma coroutine, sin task nueva de por medio.
"""
import logging
import time

from infrastructure.utils.tenant_context import get_tenant
from infrastructure.utils.user_context import get_current_user_id

logger = logging.getLogger("request")


class RequestLoggingMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        inicio = time.monotonic()
        status_code = 500

        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duracion_ms = round((time.monotonic() - inicio) * 1000, 1)
            logger.info(
                "request",
                extra={
                    "ruta": scope.get("path", ""),
                    "metodo": scope.get("method", ""),
                    "status": status_code,
                    "duracion_ms": duracion_ms,
                    "taller": get_tenant(),
                    "usuario": get_current_user_id(),
                },
            )
