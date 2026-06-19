import asyncio
import sys
from contextlib import asynccontextmanager
import psycopg
import uvicorn
from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
# from opentelemetry import trace
# from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
# from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
# from opentelemetry.instrumentation.psycopg import PsycopgInstrumentor
# from opentelemetry.sdk.trace import TracerProvider
# from opentelemetry.sdk.trace.export import BatchSpanProcessor
# from opentelemetry.trace.status import Status, StatusCode
from starlette.exceptions import HTTPException
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware

from api import api_router
from config import settings
from infrastructure.exceptions.domain_exception import DomainException
from repository.data.db_pool import init_pool, close_pool

# psycopg async en Windows requiere SelectorEventLoop (el ProactorEventLoop por
# defecto no soporta add_reader/add_writer que usa psycopg para I/O asíncrono).
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    print("🔧 Usando SelectorEventLoop para compatibilidad con psycopg en Windows")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Maneja el ciclo de vida de la aplicación (startup y shutdown)"""
    # Startup
    try:
        await init_pool()
        print("🚀 Aplicación iniciada correctamente")
    except Exception as e:
        print(f"❌ Error en startup: {e}")
        raise

    yield  # La aplicación está corriendo

    # Shutdown
    try:
        await close_pool()
        print("👋 Aplicación cerrada correctamente")
    except Exception as e:
        print(f"❌ Error en shutdown: {e}")


app = FastAPI(
    title=settings.project_name,
    openapi_url="/api/v1/openapi.json",
    docs_url=settings.docs_url,
    lifespan=lifespan,  # Usar lifespan en lugar de on_event
)

# trace.set_tracer_provider(TracerProvider())
# otlp_exporter = OTLPSpanExporter(insecure=True)
# trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(otlp_exporter))

# FastAPIInstrumentor.instrument_app(app)
# PsycopgInstrumentor().instrument()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.allowed_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=500)
app.include_router(api_router, prefix=settings.api_url)


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(
    request: Request, exc: RequestValidationError
):
    print(exc)
    # current_span = trace.get_current_span()
    # current_span.record_exception(exc)
    # current_span.set_status(Status(StatusCode.ERROR, str(exc)))
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder(
            {"message": "Ha ocurrido un error, intente mas tarde."}
        ),
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    print(exc)
    # current_span = trace.get_current_span()
    # current_span.record_exception(exc)
    # current_span.set_status(Status(StatusCode.ERROR, str(exc)))
    return JSONResponse(
        status_code=exc.status_code,
        content=jsonable_encoder(
            {"detail": exc.detail}
        ),
    )


@app.exception_handler(DomainException)
async def domain_exception_handler(request, exc: DomainException):
    print(exc)
    # current_span = trace.get_current_span()
    # current_span.record_exception(exc)
    # current_span.set_status(Status(StatusCode.ERROR, str(exc)))
    return JSONResponse(
        status_code=exc.code,
        content=jsonable_encoder({"message": exc.message}),
    )


@app.exception_handler(psycopg.Error)
async def db_exception_handler(request, exc: Exception):
    print(exc)
    # current_span = trace.get_current_span()
    # current_span.record_exception(exc)
    # current_span.set_status(Status(StatusCode.ERROR, str(exc)))
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=jsonable_encoder(
            {"message": "Ha ocurrido un error, intente mas tarde."}
        ),
    )


@app.get("/")
async def health_check():
    return {"message": "healthy"}




if __name__ == "__main__":
    uvicorn.run(
        "main:app",  # 🔥 String de importación para que funcione reload
        host="0.0.0.0",
        port=8000,
        reload=True,  # Hot reload habilitado
        reload_dirs=["api", "domain", "infrastructure", "repository"],  # Directorios a observar
        log_level="info"
    )
