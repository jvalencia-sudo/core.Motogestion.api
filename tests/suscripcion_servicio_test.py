"""procesar_webhook activa suscripciones con dinero real: la firma inválida debe
rechazarse y un webhook duplicado NO debe cobrar/activar dos veces (idempotencia)."""
from unittest.mock import AsyncMock, patch

import pytest

from domain.services.suscripciones.suscripcion_servicio import SuscripcionServicio
from infrastructure.exceptions.domain_exception import DomainException

PAYLOAD_BASE = {
    "timestamp": 123,
    "data": {"transaction": {"id": "tx-1", "reference": "MG-1-abc", "status": "APPROVED"}},
    "signature": {"properties": ["transaction.id"], "checksum": "cualquiera"},
}


def _servicio_con_mocks(pago_existente=None):
    servicio = SuscripcionServicio()
    servicio.pago_repo = AsyncMock()
    servicio.taller_repo = AsyncMock()
    servicio.pago_repo.get_por_referencia.return_value = pago_existente
    return servicio


async def test_firma_invalida_rechaza_con_401_y_no_toca_nada():
    servicio = _servicio_con_mocks()
    with patch(
        "domain.services.suscripciones.suscripcion_servicio.wompi_provider.verificar_evento",
        return_value=False,
    ):
        with pytest.raises(DomainException) as exc:
            await servicio.procesar_webhook(PAYLOAD_BASE)

    assert exc.value.code == 401
    servicio.pago_repo.get_por_referencia.assert_not_called()
    servicio.taller_repo.activar_suscripcion.assert_not_called()


async def test_pago_aprobado_activa_suscripcion_y_marca_el_pago():
    pago = {"COD_PAGO": 1, "COD_TALLER": 1, "NOMBRE_PLAN": "Premium", "ESTADO": "PENDING"}
    servicio = _servicio_con_mocks(pago_existente=pago)
    with patch(
        "domain.services.suscripciones.suscripcion_servicio.wompi_provider.verificar_evento",
        return_value=True,
    ):
        resultado = await servicio.procesar_webhook(PAYLOAD_BASE)

    assert resultado["estado"] == "APPROVED"
    servicio.pago_repo.marcar_estado.assert_awaited_once_with("MG-1-abc", "APPROVED", "tx-1")
    servicio.taller_repo.activar_suscripcion.assert_awaited_once_with(1, "Premium", 30)


async def test_webhook_duplicado_no_activa_ni_cobra_dos_veces():
    """Idempotencia: si el pago ya no está PENDING (Wompi reenvió el mismo evento,
    o llegó dos veces), el webhook no debe volver a activar la suscripción."""
    pago_ya_procesado = {
        "COD_PAGO": 1, "COD_TALLER": 1, "NOMBRE_PLAN": "Premium", "ESTADO": "APPROVED",
    }
    servicio = _servicio_con_mocks(pago_existente=pago_ya_procesado)
    with patch(
        "domain.services.suscripciones.suscripcion_servicio.wompi_provider.verificar_evento",
        return_value=True,
    ):
        resultado = await servicio.procesar_webhook(PAYLOAD_BASE)

    assert resultado["ignored"] == "pago ya procesado"
    servicio.taller_repo.activar_suscripcion.assert_not_called()
    servicio.pago_repo.marcar_estado.assert_not_called()


async def test_referencia_desconocida_se_ignora_sin_lanzar():
    servicio = _servicio_con_mocks(pago_existente=None)
    with patch(
        "domain.services.suscripciones.suscripcion_servicio.wompi_provider.verificar_evento",
        return_value=True,
    ):
        resultado = await servicio.procesar_webhook(PAYLOAD_BASE)

    assert resultado["ignored"] == "referencia desconocida"
    servicio.taller_repo.activar_suscripcion.assert_not_called()


async def test_pago_rechazado_marca_declined_sin_activar_suscripcion():
    pago = {"COD_PAGO": 1, "COD_TALLER": 1, "NOMBRE_PLAN": "Premium", "ESTADO": "PENDING"}
    servicio = _servicio_con_mocks(pago_existente=pago)
    payload_declined = {
        **PAYLOAD_BASE,
        "data": {"transaction": {"id": "tx-2", "reference": "MG-1-abc", "status": "DECLINED"}},
    }
    with patch(
        "domain.services.suscripciones.suscripcion_servicio.wompi_provider.verificar_evento",
        return_value=True,
    ):
        resultado = await servicio.procesar_webhook(payload_declined)

    assert resultado["estado"] == "DECLINED"
    servicio.pago_repo.marcar_estado.assert_awaited_once_with("MG-1-abc", "DECLINED", "tx-2")
    servicio.taller_repo.activar_suscripcion.assert_not_called()
