from fastapi import APIRouter, Request

from domain.contracts.ordenes_trabajo.orden_trabajo_contract import (
    AprobarCotizacionResponseContract,
    OrdenPublicaResponseContract,
)
from domain.services.ordenes_trabajo.orden_aprobacion_servicio import OrdenAprobacionServicio
from domain.services.ordenes_trabajo.orden_trabajo_publica_servicio import (
    OrdenTrabajoPublicaServicio,
)
from infrastructure.utils.client_ip import ip_cliente
from infrastructure.utils.rate_limiter import limiter

router = APIRouter()


@router.get("/ordenes-trabajo/estado/{token}", response_model=OrdenPublicaResponseContract)
@limiter.limit("30/minute")
async def estado_publico_orden(token: str, request: Request):
    """F2-01: link PÚBLICO de estado de una orden (sin login). La identidad
    la da el UUID impredecible del token, no una sesión -- un token
    inexistente o con un carácter cambiado da 404 (nunca distingue el
    motivo). Rate limit por IP (F2-02): este endpoint no tiene ningún otro
    control de acceso."""
    return await OrdenTrabajoPublicaServicio().obtener_por_token(token)


@router.patch(
    "/ordenes-trabajo/{token}/aprobar", response_model=AprobarCotizacionResponseContract
)
@limiter.limit("5/minute")
async def aprobar_cotizacion_publica(token: str, request: Request):
    """F2-03: aprueba la cotización vigente de una orden desde el link
    público (sin sesión, protegido solo por el token). Opcional por taller
    (ver talleres.exige_aprobacion_cotizacion_tal) -- 409 si la orden no
    aplica. Idempotente: aprobar dos veces no duplica registros. Límite más
    estricto que el GET de estado porque además escribe."""
    return await OrdenAprobacionServicio().aprobar(
        token, ip_cliente(request), request.headers.get("user-agent")
    )
