"""F0-13 (revisión): fn_calc_fecha_garantia (trigger de ordenes_trabajo)
pisaba SIEMPRE fecha_fin_garantia_ot con "entrega + 1 mes" fijo, sin importar
qué dias_garantia_pred tuviera configurado el taller en "Mi taller" ni qué
hubiera calculado la app -- reproducido por la revisión: configurar 90 días
dejaba la orden con 31 días de garantía igual. Estos tests van directo contra
Postgres (sin pasar por el servicio) porque el bug vive en el trigger, no en
Python -- un mock de repositorio nunca lo habría detectado."""
from datetime import date, timedelta

import pytest

from tests.conftest import TALLER_A

pytestmark = pytest.mark.db


@pytest.fixture
def dias_garantia_90(db_conn, seed_talleres):
    """Configura dias_garantia_pred=90 en TALLER_A (default de fábrica: 30) y
    lo restaura al terminar, para no filtrar estado a otros tests del módulo."""
    with db_conn.cursor() as cur:
        cur.execute(
            "UPDATE talleres SET dias_garantia_pred = 90 WHERE cod_taller = %s", (TALLER_A,)
        )
    yield 90
    with db_conn.cursor() as cur:
        cur.execute(
            "UPDATE talleres SET dias_garantia_pred = 30 WHERE cod_taller = %s", (TALLER_A,)
        )


def test_entregar_con_fecha_fin_garantia_explicita_no_se_pisa(db_conn, seed_talleres, dias_garantia_90):
    """Simula exactamente lo que hace registrar_entrega(): un UPDATE que trae
    cod_ot_est_ot=4 y fecha_fin_garantia_ot YA calculada (con los 90 días del
    taller) en la misma sentencia. El trigger no debe recalcularla."""
    seed = seed_talleres[TALLER_A]
    hoy = date.today()
    fecha_fin_calculada = hoy + timedelta(days=dias_garantia_90)

    with db_conn.cursor() as cur:
        cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(TALLER_A),))
        cur.execute(
            "UPDATE ordenes_trabajo SET cod_ot_est_ot = 4, fecha_entrega_ot = %s, "
            "fecha_fin_garantia_ot = %s WHERE cod_taller = %s AND consecutivo_ot = %s",
            (hoy, fecha_fin_calculada, TALLER_A, seed.consecutivo_ot),
        )
        cur.execute(
            "SELECT fecha_fin_garantia_ot FROM ordenes_trabajo "
            "WHERE cod_taller = %s AND consecutivo_ot = %s",
            (TALLER_A, seed.consecutivo_ot),
        )
        resultado = cur.fetchone()[0]

    assert resultado == fecha_fin_calculada
    # El bug reportado: el trigger la dejaba en entrega + 1 mes (~31 días) sin
    # importar los 90 configurados.
    assert resultado != hoy + timedelta(days=31)


def test_cambiar_estado_a_entregada_sin_fecha_explicita_usa_dias_garantia_pred(
    db_conn, seed_talleres, dias_garantia_90
):
    """Si algo cambia el estado a 4 SIN tocar fecha_fin_garantia_ot (ej. un
    cambio de estado genérico, no el flujo dedicado de entrega), el trigger sí
    debe autocalcularla -- pero con dias_garantia_pred del taller (90), no con
    el "+1 mes" fijo de antes."""
    seed = seed_talleres[TALLER_A]
    hoy = date.today()

    with db_conn.cursor() as cur:
        cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(TALLER_A),))
        cur.execute(
            "UPDATE ordenes_trabajo SET cod_ot_est_ot = 4, fecha_entrega_ot = %s "
            "WHERE cod_taller = %s AND consecutivo_ot = %s",
            (hoy, TALLER_A, seed.consecutivo_ot),
        )
        cur.execute(
            "SELECT fecha_fin_garantia_ot FROM ordenes_trabajo "
            "WHERE cod_taller = %s AND consecutivo_ot = %s",
            (TALLER_A, seed.consecutivo_ot),
        )
        resultado = cur.fetchone()[0]

    assert resultado == hoy + timedelta(days=90)
