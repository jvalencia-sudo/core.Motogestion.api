"""obtener_suscripcion arma el estado de suscripción que ve el front (banner +
vista de 'Suscripción' en Administración): días restantes, si está vencido, el
precio pactado y desde cuándo es miembro el taller."""
from datetime import date, timedelta
from unittest.mock import AsyncMock

import pytest

from domain.services.talleres.taller_servicio import TallerServicio
from infrastructure.exceptions.domain_exception import DomainException
from infrastructure.utils.fecha_bogota import hoy_bogota


def _servicio_con_mock(get_suscripcion_return):
    servicio = TallerServicio()
    servicio.repository = AsyncMock()
    servicio.repository.get_suscripcion.return_value = get_suscripcion_return
    return servicio


async def test_taller_no_encontrado_lanza_404():
    servicio = _servicio_con_mock(None)

    with pytest.raises(DomainException) as exc:
        await servicio.obtener_suscripcion(999)
    assert exc.value.code == 404


async def test_taller_en_prueba_calcula_dias_restantes():
    fecha_fin = hoy_bogota() + timedelta(days=12)
    servicio = _servicio_con_mock({
        "ESTADO_TAL": "prueba",
        "PLAN_TAL": None,
        "FECHA_FIN_SUSC_TAL": fecha_fin,
        "PRECIO_SUSC_TAL": None,
        "FECHA_CREACION_TAL": hoy_bogota() - timedelta(days=18),
    })

    resultado = await servicio.obtener_suscripcion(1)

    assert resultado.estado == "prueba"
    assert resultado.dias_restantes == 12
    assert resultado.vencido is False
    assert resultado.precio is None


async def test_taller_con_prueba_vencida_marca_vencido():
    fecha_fin = hoy_bogota() - timedelta(days=3)
    servicio = _servicio_con_mock({
        "ESTADO_TAL": "prueba",
        "PLAN_TAL": None,
        "FECHA_FIN_SUSC_TAL": fecha_fin,
        "PRECIO_SUSC_TAL": None,
        "FECHA_CREACION_TAL": hoy_bogota() - timedelta(days=33),
    })

    resultado = await servicio.obtener_suscripcion(1)

    assert resultado.vencido is True
    assert resultado.dias_restantes == -3


async def test_taller_activo_incluye_precio_pactado_y_miembro_desde():
    servicio = _servicio_con_mock({
        "ESTADO_TAL": "activo",
        "PLAN_TAL": "Taller",
        "FECHA_FIN_SUSC_TAL": date(2026, 12, 13),
        "PRECIO_SUSC_TAL": 49000,
        "FECHA_CREACION_TAL": date(2026, 9, 1),
    })

    resultado = await servicio.obtener_suscripcion(1)

    assert resultado.estado == "activo"
    assert resultado.plan == "Taller"
    assert resultado.precio == 49000
    assert resultado.fecha_fin == "2026-12-13"
    assert resultado.miembro_desde == "2026-09-01"
    # Un taller "activo" nunca se marca vencido aunque fecha_fin ya haya
    # pasado alguna vez -- vencido solo aplica a la prueba gratis.
    assert resultado.vencido is False
