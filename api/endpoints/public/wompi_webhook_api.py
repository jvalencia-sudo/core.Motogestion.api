from fastapi import APIRouter, Request

from domain.services.suscripciones.suscripcion_servicio import SuscripcionServicio

router = APIRouter()


@router.post("/wompi/webhook")
async def wompi_webhook(request: Request):
    """Webhook PÚBLICO de Wompi (sin auth; se valida por firma del evento).
    Al aprobarse el pago, activa la suscripción del taller."""
    payload = await request.json()
    return await SuscripcionServicio().procesar_webhook(payload)
