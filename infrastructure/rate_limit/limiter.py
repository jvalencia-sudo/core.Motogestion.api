"""Rate limiting de la API (en memoria, por IP).

Usa slowapi (sobre `limits`). La clave es la IP del cliente: como la app corre
detrás de Traefik, se lee X-Forwarded-For para obtener la IP real en lugar de la
del proxy. El almacenamiento es en memoria (una sola instancia): los contadores se
reinician al reiniciar la app.

- `limiter.default_limits` aplica un límite global a TODA la API vía SlowAPIMiddleware.
- Endpoints sensibles (login, registro) usan `@limiter.limit(...)` para un límite
  más estricto, además del global.

Los límites se pueden ajustar por variables de entorno (ver config.RateLimitConfig).
"""
from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from config import settings


def _client_ip(request: Request) -> str:
    """IP real del cliente respetando el proxy (Traefik).

    Asume UN único proxy de confianza delante de la app (Traefik). En ese caso
    X-Forwarded-For queda como "<falsificable_por_cliente>, ..., <ip_real>": Traefik
    AÑADE la IP de la conexión al final, así que la IP real es el ÚLTIMO valor.

    Tomar el PRIMER valor sería inseguro: un atacante podría mandar su propio
    X-Forwarded-For y evadir el límite rotando IPs falsas. Por eso usamos el último.

    Si algún día se añade otro proxy/CDN por delante de Traefik, habría que ajustar
    cuántos saltos de confianza descontar. Sin el header, se usa la IP de la conexión.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        parts = [p.strip() for p in forwarded.split(",") if p.strip()]
        if parts:
            return parts[-1]
    return get_remote_address(request)


limiter = Limiter(
    key_func=_client_ip,
    default_limits=[settings.rate_limit_config.default],
    enabled=settings.rate_limit_config.enabled,
    headers_enabled=True,  # añade X-RateLimit-* a las respuestas
)


def rate_limit_exceeded_handler(
    request: Request, exc: RateLimitExceeded
) -> JSONResponse:
    """Devuelve 429 con el formato de error del proyecto ({"message": ...}).

    Es síncrono a propósito: SlowAPIMiddleware descarta los handlers async y cae
    en el handler por defecto de slowapi (ver slowapi/middleware.py sync_check_limits).
    """
    response = JSONResponse(
        status_code=429,
        content=jsonable_encoder(
            {"message": "Demasiadas solicitudes, intente mas tarde."}
        ),
    )
    # Cabeceras informativas (Retry-After, X-RateLimit-*) que slowapi calcula.
    view_rate_limit = getattr(request.state, "view_rate_limit", None)
    if view_rate_limit is not None:
        request.app.state.limiter._inject_headers(response, view_rate_limit)
    return response
