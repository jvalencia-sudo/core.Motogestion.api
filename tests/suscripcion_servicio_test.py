"""procesar_webhook activa suscripciones con dinero real: la firma inválida debe
rechazarse, un monto que no cuadra con lo esperado no debe activar nada, y un
webhook duplicado NO debe cobrar/activar dos veces (idempotencia).

_calcular_monto_a_pagar decide cuánto paga un taller (F0-08: precio fundador
para los primeros CUPOS_FUNDADOR, precio ya pactado se congela, catálogo
vigente para el resto) -- también se prueba directo, sin pasar por el webhook."""
from unittest.mock import AsyncMock, patch

import pytest

from domain.services.suscripciones.suscripcion_servicio import (
    CUPOS_FUNDADOR,
    PRECIO_FUNDADOR,
    SuscripcionServicio,
)
from infrastructure.exceptions.domain_exception import DomainException
from infrastructure.providers.payments import wompi_provider

MONTO = 49000
PAYLOAD_BASE = {
    "timestamp": 123,
    "data": {
        "transaction": {
            "id": "tx-1", "reference": "MG-1-abc", "status": "APPROVED",
            "amount_in_cents": MONTO * 100,
        }
    },
    "signature": {"properties": ["transaction.id"], "checksum": "cualquiera"},
}


def _servicio_con_mocks(pago_existente=None, precio_susc_tal=None):
    servicio = SuscripcionServicio()
    servicio.pago_repo = AsyncMock()
    servicio.taller_repo = AsyncMock()
    servicio.pago_repo.get_por_referencia.return_value = pago_existente
    # Sin esto, `taller.get(...)` en el código real devuelve otro AsyncMock (no
    # un dict real) y crea una corrutina sin awaitear -- un taller real siempre
    # trae esta llave (None si nunca ha pagado).
    servicio.taller_repo.get_suscripcion.return_value = {"PRECIO_SUSC_TAL": precio_susc_tal}
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
    pago = {"COD_PAGO": 1, "COD_TALLER": 1, "NOMBRE_PLAN": "Taller", "ESTADO": "PENDING", "MONTO": MONTO}
    servicio = _servicio_con_mocks(pago_existente=pago, precio_susc_tal=None)
    with patch(
        "domain.services.suscripciones.suscripcion_servicio.wompi_provider.verificar_evento",
        return_value=True,
    ):
        resultado = await servicio.procesar_webhook(PAYLOAD_BASE)

    assert resultado.estado == "APPROVED"
    servicio.pago_repo.marcar_estado.assert_awaited_once_with("MG-1-abc", "APPROVED", "tx-1")
    servicio.taller_repo.activar_suscripcion.assert_awaited_once_with(1, "Taller", 30)
    # Primer pago aprobado: congela el precio pagado en precio_susc_tal.
    servicio.taller_repo.actualizar.assert_awaited_once_with(1, {"precio_susc_tal": MONTO})


async def test_pago_aprobado_de_taller_que_ya_tenia_precio_pactado_no_lo_vuelve_a_escribir():
    """El taller ya pagó antes (ya tiene precio_susc_tal): no hay que tocarlo de
    nuevo en cada renovación mensual."""
    pago = {"COD_PAGO": 2, "COD_TALLER": 1, "NOMBRE_PLAN": "Taller", "ESTADO": "PENDING", "MONTO": MONTO}
    servicio = _servicio_con_mocks(pago_existente=pago, precio_susc_tal=MONTO)
    with patch(
        "domain.services.suscripciones.suscripcion_servicio.wompi_provider.verificar_evento",
        return_value=True,
    ):
        await servicio.procesar_webhook(PAYLOAD_BASE)

    servicio.taller_repo.actualizar.assert_not_called()


async def test_webhook_con_monto_distinto_al_esperado_no_activa_nada():
    """El monto que llega del webhook no coincide con lo que se esperaba cobrar
    (pago.MONTO): no se activa la suscripción ni se congela ningún precio."""
    pago = {"COD_PAGO": 1, "COD_TALLER": 1, "NOMBRE_PLAN": "Taller", "ESTADO": "PENDING", "MONTO": 69000}
    servicio = _servicio_con_mocks(pago_existente=pago)
    with patch(
        "domain.services.suscripciones.suscripcion_servicio.wompi_provider.verificar_evento",
        return_value=True,
    ):
        resultado = await servicio.procesar_webhook(PAYLOAD_BASE)  # paga 49000, se esperaban 69000

    assert resultado.estado == "MONTO_INVALIDO"
    servicio.taller_repo.activar_suscripcion.assert_not_called()
    servicio.taller_repo.actualizar.assert_not_called()
    servicio.pago_repo.marcar_estado.assert_awaited_once_with("MG-1-abc", "DECLINED", "tx-1")


async def test_webhook_duplicado_no_activa_ni_cobra_dos_veces():
    """Idempotencia: si el pago ya no está PENDING (Wompi reenvió el mismo evento,
    o llegó dos veces), el webhook no debe volver a activar la suscripción."""
    pago_ya_procesado = {
        "COD_PAGO": 1, "COD_TALLER": 1, "NOMBRE_PLAN": "Taller", "ESTADO": "APPROVED", "MONTO": MONTO,
    }
    servicio = _servicio_con_mocks(pago_existente=pago_ya_procesado)
    with patch(
        "domain.services.suscripciones.suscripcion_servicio.wompi_provider.verificar_evento",
        return_value=True,
    ):
        resultado = await servicio.procesar_webhook(PAYLOAD_BASE)

    assert resultado.ignored == "pago ya procesado"
    servicio.taller_repo.activar_suscripcion.assert_not_called()
    servicio.pago_repo.marcar_estado.assert_not_called()


async def test_referencia_desconocida_se_ignora_sin_lanzar():
    servicio = _servicio_con_mocks(pago_existente=None)
    with patch(
        "domain.services.suscripciones.suscripcion_servicio.wompi_provider.verificar_evento",
        return_value=True,
    ):
        resultado = await servicio.procesar_webhook(PAYLOAD_BASE)

    assert resultado.ignored == "referencia desconocida"
    servicio.taller_repo.activar_suscripcion.assert_not_called()


async def test_pago_rechazado_marca_declined_sin_activar_suscripcion():
    pago = {"COD_PAGO": 1, "COD_TALLER": 1, "NOMBRE_PLAN": "Taller", "ESTADO": "PENDING", "MONTO": MONTO}
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

    assert resultado.estado == "DECLINED"
    servicio.pago_repo.marcar_estado.assert_awaited_once_with("MG-1-abc", "DECLINED", "tx-2")
    servicio.taller_repo.activar_suscripcion.assert_not_called()


# ---- _calcular_monto_a_pagar ----

async def test_con_9_fundadores_el_siguiente_taller_paga_precio_fundador():
    servicio = _servicio_con_mocks()
    servicio.taller_repo.contar_por_precio_susc.return_value = CUPOS_FUNDADOR - 1

    monto = await servicio._calcular_monto_a_pagar(cod_taller=99, precio_plan=69000)

    assert monto == PRECIO_FUNDADOR
    servicio.taller_repo.contar_por_precio_susc.assert_awaited_once_with(PRECIO_FUNDADOR)


async def test_con_10_fundadores_el_siguiente_taller_paga_precio_de_catalogo():
    servicio = _servicio_con_mocks()
    servicio.taller_repo.contar_por_precio_susc.return_value = CUPOS_FUNDADOR

    monto = await servicio._calcular_monto_a_pagar(cod_taller=99, precio_plan=69000)

    assert monto == 69000


async def test_taller_con_precio_pactado_paga_ese_precio_sin_mirar_el_cupo():
    """Aunque ya no queden cupos fundador, un taller que YA tiene precio_susc_tal
    sigue pagando lo que tiene pactado (p.ej. renovaciones, o un ajuste manual)."""
    servicio = _servicio_con_mocks(precio_susc_tal=49000)
    servicio.taller_repo.contar_por_precio_susc.return_value = CUPOS_FUNDADOR  # cupos agotados

    monto = await servicio._calcular_monto_a_pagar(cod_taller=1, precio_plan=69000)

    assert monto == 49000
    servicio.taller_repo.contar_por_precio_susc.assert_not_called()


async def test_cambiar_precio_plan_no_altera_lo_que_paga_un_taller_con_precio_pactado():
    """El precio pactado (precio_susc_tal) es independiente del precio_plan que
    se le pase a la función: aunque el catálogo suba o baje, no cambia."""
    servicio = _servicio_con_mocks(precio_susc_tal=49000)

    monto_con_precio_viejo = await servicio._calcular_monto_a_pagar(cod_taller=1, precio_plan=69000)
    monto_con_precio_nuevo = await servicio._calcular_monto_a_pagar(cod_taller=1, precio_plan=89000)

    assert monto_con_precio_viejo == monto_con_precio_nuevo == 49000


async def test_sin_taller_cod_taller_none_calcula_el_precio_de_un_taller_nuevo():
    """La landing pública (sin sesión) no tiene cod_taller: debe poder calcular
    igual lo que pagaría un taller nuevo, sin reventar."""
    servicio = _servicio_con_mocks()
    servicio.taller_repo.contar_por_precio_susc.return_value = 0

    monto = await servicio._calcular_monto_a_pagar(cod_taller=None, precio_plan=69000)

    assert monto == PRECIO_FUNDADOR
    servicio.taller_repo.get_suscripcion.assert_not_called()


async def test_plan_gratis_no_entra_en_el_calculo_de_fundador():
    servicio = _servicio_con_mocks()

    monto = await servicio._calcular_monto_a_pagar(cod_taller=None, precio_plan=0)

    assert monto == 0
    servicio.taller_repo.contar_por_precio_susc.assert_not_called()


# ---- crear_checkout: plan inactivo ----

async def test_checkout_con_plan_inexistente_o_inactivo_responde_400():
    servicio = SuscripcionServicio()
    servicio.plan_repo = AsyncMock()
    servicio.plan_repo.get_por_nombre.return_value = {"PRECIO_PLAN": 99000, "ACTIVO": False}

    with patch("domain.services.suscripciones.suscripcion_servicio.settings") as settings_mock:
        settings_mock.wompi_config.configurado = True
        with pytest.raises(DomainException) as exc:
            await servicio.crear_checkout(cod_taller=1, nombre_plan="Premium")

    assert exc.value.code == 400


# ---- crear_checkout: datos del Widget de Wompi (modal, F1-xx) ----

async def test_checkout_devuelve_los_datos_del_widget_con_firma_correcta():
    """El front abre el Widget de Wompi con estos campos (sin redirect a una
    URL de Wompi) -- la firma debe coincidir exactamente con la que Wompi
    recalcula de su lado, o el pago se rechaza."""
    servicio = SuscripcionServicio()
    servicio.plan_repo = AsyncMock()
    servicio.plan_repo.get_por_nombre.return_value = {"PRECIO_PLAN": MONTO, "ACTIVO": True}
    servicio.pago_repo = AsyncMock()
    servicio.taller_repo = AsyncMock()
    servicio.taller_repo.get_suscripcion.return_value = {"PRECIO_SUSC_TAL": None}
    servicio.taller_repo.contar_por_precio_susc.return_value = CUPOS_FUNDADOR  # sin cupo: paga catálogo

    with patch("domain.services.suscripciones.suscripcion_servicio.settings") as settings_mock:
        settings_mock.wompi_config.configurado = True
        settings_mock.wompi_config.public_key = "pub_test_abc"
        settings_mock.wompi_config.integrity_secret = "secreto"

        resp = await servicio.crear_checkout(cod_taller=1, nombre_plan="Premium")

    assert resp.public_key == "pub_test_abc"
    assert resp.currency == "COP"
    assert resp.amount_in_cents == MONTO * 100
    firma_esperada = wompi_provider.firma_integridad(
        resp.reference, MONTO * 100, "COP", "secreto"
    )
    assert resp.signature == firma_esperada


# ---- listar_pagos: historial de pagos del taller (vista de Administración) ----

async def test_listar_pagos_mapea_las_filas_crudas_de_la_bd_a_pagocontract():
    """pago_repo.listar_por_taller devuelve dicts con las columnas crudas en
    MAYÚSCULAS (BaseRepository): listar_pagos debe mapearlas a PagoContract, no
    devolver el dict crudo (eso rompía el camelCase que espera el front)."""
    servicio = SuscripcionServicio()
    servicio.pago_repo = AsyncMock()
    servicio.pago_repo.listar_por_taller.return_value = [
        {
            "COD_PAGO": 3, "NOMBRE_PLAN": "Taller", "MONTO": 49000,
            "ESTADO": "APPROVED", "FECHA": "2026-10-15 01:17",
        },
        {
            "COD_PAGO": 2, "NOMBRE_PLAN": "Taller", "MONTO": 49000,
            "ESTADO": "PENDING", "FECHA": "2026-10-15 01:11",
        },
    ]

    pagos = await servicio.listar_pagos(cod_taller=2)

    assert len(pagos) == 2
    assert pagos[0].cod_pago == 3
    assert pagos[0].nombre_plan == "Taller"
    assert pagos[0].monto == 49000
    assert pagos[0].estado == "APPROVED"
    assert pagos[0].fecha == "2026-10-15 01:17"
    assert pagos[1].estado == "PENDING"


async def test_listar_pagos_de_un_taller_sin_pagos_devuelve_lista_vacia():
    servicio = SuscripcionServicio()
    servicio.pago_repo = AsyncMock()
    servicio.pago_repo.listar_por_taller.return_value = []

    pagos = await servicio.listar_pagos(cod_taller=5)

    assert pagos == []
