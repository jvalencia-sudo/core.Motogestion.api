import asyncio
import logging
import sys
from contextlib import asynccontextmanager
import psycopg
import sentry_sdk
import uvicorn
from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware

from fastapi import Depends

from api import api_router
from config import settings
from infrastructure.dependencies.tenant_request import resolve_tenant
from infrastructure.exceptions.domain_exception import DomainException
from infrastructure.middleware.request_logging import RequestLoggingMiddleware
from infrastructure.utils.logging_config import configurar_logging
from infrastructure.utils.ruta_plantilla import ruta_plantilla
from infrastructure.utils.sentry_scrub import scrub_before_send
from repository.data.db_pool import init_pool, close_pool, get_pool

configurar_logging()
logger = logging.getLogger(__name__)

if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.environment,
        release=settings.sentry_release or None,
        send_default_pii=False,
        # Sentry serializa las variables locales de cada frame con su repr como
        # texto plano (p.ej. "ClienteModelo(documento_cli='1122334455', ...)") --
        # el scrub por clave de scrub_before_send no puede limpiar eso porque no
        # es un diccionario. Más vale no mandar locals que mandarlos sin filtrar.
        include_local_variables=False,
        before_send=scrub_before_send,
    )

# psycopg async en Windows requiere SelectorEventLoop (el ProactorEventLoop por
# defecto no soporta add_reader/add_writer que usa psycopg para I/O asíncrono).
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    logger.info("Usando SelectorEventLoop para compatibilidad con psycopg en Windows")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Maneja el ciclo de vida de la aplicación (startup y shutdown)"""
    # Startup
    try:
        await init_pool()
        logger.info("Aplicación iniciada correctamente")
    except Exception:
        logger.exception("Error en startup")
        raise

    yield  # La aplicación está corriendo

    # Shutdown
    try:
        await close_pool()
        logger.info("Aplicación cerrada correctamente")
    except Exception:
        logger.exception("Error en shutdown")


app = FastAPI(
    title=settings.project_name,
    openapi_url="/api/v1/openapi.json",
    docs_url=settings.docs_url,
    lifespan=lifespan,  # Usar lifespan en lugar de on_event
)

# Orden importante: Starlette envuelve el ASGI app con el último middleware agregado
# como capa más externa. CORS va al final para que quede afuera de todo: así los
# encabezados CORS también se aplican a respuestas de error de las demás capas, y el
# preflight (OPTIONS) se resuelve antes de pasar por logging/gzip.
app.add_middleware(GZipMiddleware, minimum_size=500)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix=settings.api_url, dependencies=[Depends(resolve_tenant)])


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(
    request: Request, exc: RequestValidationError
):
    # Solo loc/msg/type, nunca la clave "input": ahí Pydantic v2 guarda el valor
    # rechazado, y un login/registro/alta de cliente mal formado lo dejaría en los
    # logs (contraseña, documento, etc).
    errores = [
        {"loc": e.get("loc"), "msg": e.get("msg"), "type": e.get("type")}
        for e in exc.errors()
    ]
    logger.warning("Error de validación en %s: %s", ruta_plantilla(request.scope), errores)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder(
            {"message": "Ha ocurrido un error, intente mas tarde."}
        ),
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    logger.warning("HTTPException %s en %s: %s", exc.status_code, ruta_plantilla(request.scope), exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content=jsonable_encoder(
            {"detail": exc.detail}
        ),
    )


@app.exception_handler(DomainException)
async def domain_exception_handler(request, exc: DomainException):
    logger.warning("DomainException %s en %s: %s", exc.code, ruta_plantilla(request.scope), exc.message)
    return JSONResponse(
        status_code=exc.code,
        content=jsonable_encoder({"message": exc.message}),
    )


@app.exception_handler(psycopg.Error)
async def db_exception_handler(request, exc: psycopg.Error):
    # Nunca el mensaje completo de psycopg: exc.diag.message_detail trae la fila
    # que violó la restricción (p.ej. "DETAIL: Key (documento_cli)=(1122334455)
    # already exists"), con datos reales del cliente. message_primary alcanza para
    # diagnosticar ("duplicate key value violates unique constraint...") sin la fila.
    # No hace falta capture_exception acá: la integración de logging de Sentry ya
    # convierte este logger.error(exc_info=...) en un evento por sí sola (con
    # scrub_before_send aplicado igual) -- llamarlo también mandaría el error dos
    # veces y gastaría el doble de cuota. exc_info=exc se deja (da el traceback
    # real en Sentry); el str(exc) de psycopg trae igual el DETAIL con la fila
    # completa, por eso scrub_before_send lo limpia también ahí, no solo acá.
    logger.error(
        "Error de base de datos en %s: [%s] %s",
        ruta_plantilla(request.scope),
        exc.sqlstate,
        exc.diag.message_primary if exc.diag else str(exc),
        exc_info=exc,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=jsonable_encoder(
            {"message": "Ha ocurrido un error, intente mas tarde."}
        ),
    )


@app.get("/")
async def health_check():
    return {"message": "healthy"}


@app.get("/health")
async def health():
    """Endpoint de salud para el healthcheck de Docker/Traefik: solo confirma que
    el proceso responde. A propósito NO toca la BD (Docker lo llama cada pocos
    segundos; una BD momentáneamente lenta no debe reiniciar el contenedor)."""
    return {"status": "ok"}


@app.get("/health/ready")
async def health_ready():
    """Para el monitor de disponibilidad externo (Better Stack/UptimeRobot): a
    diferencia de /health, sí confirma que Postgres responde. Si la BD se cae,
    /health seguiría en "ok" (el proceso vive) mientras todas las peticiones
    reales fallan -- este endpoint es el que debe vigilar el monitor externo."""
    try:
        async with asyncio.timeout(3):
            async with get_pool().connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT 1")
    except Exception:
        logger.error("health/ready: la BD no respondió")
        raise HTTPException(status_code=503, detail="not ready")
    return {"status": "ok"}




if __name__ == "__main__":
    uvicorn.run(
        "main:app",  # 🔥 String de importación para que funcione reload
        host="0.0.0.0",
        port=8000,
        reload=True,  # Hot reload habilitado
        reload_dirs=["api", "domain", "infrastructure", "repository"],  # Directorios a observar
        log_level="info"
    )
