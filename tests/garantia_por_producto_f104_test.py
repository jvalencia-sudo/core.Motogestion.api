"""F1-04: la garantía de una orden la fijaba un trigger con el número de días
configurado en "Mi taller" (dias_garantia_pred), igual para toda orden sin
importar qué se hizo -- el campo manual del formulario (con su validación de
"mínimo 30 días") nunca tenía efecto real. Ahora la da el servicio/producto
más largo de la orden (MAX(dias_garantia_pro) de sus ítems); 0 = sin
garantía. Los tests del trigger van directo contra Postgres (sin pasar por
el servicio), igual que garantia_pred_trigger_test.py antes de esta reescritura:
el cálculo vive en el trigger, no en Python."""
from datetime import date, timedelta

import pytest

from tests.conftest import TALLER_A, auth_headers

# mock_auth0 no es autouse (ver conftest.py): las clases de abajo hacen
# requests HTTP autenticados con auth_headers(), así que lo necesita el
# archivo entero (los tests que solo tocan la BD lo ignoran sin problema).
pytestmark = [pytest.mark.db, pytest.mark.usefixtures("mock_auth0")]


@pytest.fixture
def orden_limpia(db_conn, seed_talleres):
    """Restaura la orden sembrada a Pendiente, sin fechas de entrega/garantía
    y con un único detalle (el BIEN sembrado, dias_garantia_pro=0 por
    default), antes y después de cada test -- mismo motivo que
    anular_orden_f105_test.py: cada test parte de un estado limpio sin
    importar en qué quedó el anterior (seed_talleres es scope=module)."""
    seed = seed_talleres[TALLER_A]

    def _restaurar():
        with db_conn.cursor() as cur:
            cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(TALLER_A),))
            cur.execute(
                "UPDATE ordenes_trabajo SET cod_ot_est_ot = 1, fecha_entrega_ot = NULL, "
                "fecha_fin_garantia_ot = NULL WHERE cod_taller = %s AND consecutivo_ot = %s",
                (TALLER_A, seed.consecutivo_ot),
            )
            cur.execute(
                "DELETE FROM detalle_orden_trabajo WHERE cod_taller = %s "
                "AND consecutivo_ot_deto = %s AND cod_pro_deto != %s",
                (TALLER_A, seed.consecutivo_ot, seed.cod_producto),
            )
            cur.execute(
                "SELECT count(*) FROM detalle_orden_trabajo "
                "WHERE cod_taller = %s AND consecutivo_ot_deto = %s AND cod_pro_deto = %s",
                (TALLER_A, seed.consecutivo_ot, seed.cod_producto),
            )
            if cur.fetchone()[0] == 0:
                cur.execute(
                    "INSERT INTO detalle_orden_trabajo (cod_taller, consecutivo_ot_deto, "
                    "cod_pro_deto, fecha_confirmacion_deto, valor_unitario_deto, cantidad_deto, "
                    "documento_usu_deto) VALUES (%s, %s, %s, CURRENT_DATE, 50000, 1, %s)",
                    (TALLER_A, seed.consecutivo_ot, seed.cod_producto, seed.documento_usuario),
                )
            cur.execute(
                "UPDATE productos SET dias_garantia_pro = 0 WHERE cod_taller = %s AND cod_pro = %s",
                (TALLER_A, seed.cod_producto),
            )

    _restaurar()
    yield seed
    _restaurar()


def _crear_servicio(db_conn, cod_taller: int, dias_garantia: int) -> int:
    """Crea un producto SERVICIO con el dias_garantia_pro indicado."""
    with db_conn.cursor() as cur:
        cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(cod_taller),))
        cur.execute(
            "INSERT INTO productos (cod_taller, nombre_pro, cod_est_pro, precio_pro, "
            "tipo_pro, dias_garantia_pro) VALUES (%s, 'Servicio de prueba', 1, 30000, "
            "'SERVICIO', %s) RETURNING cod_pro",
            (cod_taller, dias_garantia),
        )
        return cur.fetchone()[0]


def _agregar_detalle(db_conn, cod_taller: int, consecutivo_ot: int, cod_pro: int, documento_usu: str) -> None:
    with db_conn.cursor() as cur:
        cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(cod_taller),))
        cur.execute(
            "INSERT INTO detalle_orden_trabajo (cod_taller, consecutivo_ot_deto, "
            "cod_pro_deto, fecha_confirmacion_deto, valor_unitario_deto, cantidad_deto, "
            "documento_usu_deto) VALUES (%s, %s, %s, CURRENT_DATE, 30000, 1, %s)",
            (cod_taller, consecutivo_ot, cod_pro, documento_usu),
        )


def _entregar(db_conn, cod_taller: int, consecutivo_ot: int, fecha_entrega: date) -> date | None:
    """Simula registrar_entrega(): un UPDATE a cod_ot_est_ot=4 + fecha_entrega_ot,
    SIN tocar fecha_fin_garantia_ot (la fija el trigger). Devuelve lo que quedó."""
    with db_conn.cursor() as cur:
        cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(cod_taller),))
        cur.execute(
            "UPDATE ordenes_trabajo SET cod_ot_est_ot = 4, fecha_entrega_ot = %s "
            "WHERE cod_taller = %s AND consecutivo_ot = %s",
            (fecha_entrega, cod_taller, consecutivo_ot),
        )
        cur.execute(
            "SELECT fecha_fin_garantia_ot FROM ordenes_trabajo "
            "WHERE cod_taller = %s AND consecutivo_ot = %s",
            (cod_taller, consecutivo_ot),
        )
        return cur.fetchone()[0]


def test_producto_sin_garantia_se_entrega_sin_fecha_fin_garantia(db_conn, orden_limpia):
    """Un cambio de aceite (el BIEN sembrado, dias_garantia_pro=0) se entrega
    sin garantía: fecha_fin_garantia_ot queda NULL, no "entrega + 1 mes"."""
    seed = orden_limpia
    resultado = _entregar(db_conn, TALLER_A, seed.consecutivo_ot, date.today())
    assert resultado is None


def test_orden_con_items_mixtos_usa_el_maximo_de_dias_garantia(db_conn, orden_limpia):
    """Una orden con un servicio de 90 días y otro de 30 queda con garantía
    de 90 días (el máximo de sus ítems), no la suma ni el primero."""
    seed = orden_limpia
    servicio_90 = _crear_servicio(db_conn, TALLER_A, 90)
    servicio_30 = _crear_servicio(db_conn, TALLER_A, 30)
    _agregar_detalle(db_conn, TALLER_A, seed.consecutivo_ot, servicio_90, seed.documento_usuario)
    _agregar_detalle(db_conn, TALLER_A, seed.consecutivo_ot, servicio_30, seed.documento_usuario)

    hoy = date.today()
    resultado = _entregar(db_conn, TALLER_A, seed.consecutivo_ot, hoy)

    assert resultado == hoy + timedelta(days=90)


class TestReclamoValidaContraLaFechaCalculada:
    """Los reclamos (crear una orden en estado 6 "Garantía") siguen validando
    contra fecha_fin_garantia_ot de la orden anterior entregada de esa moto
    -- sin importar que ahora la calcule el MAX por ítem en vez del
    dias_garantia_pred del taller."""

    def test_garantia_vencida_rechaza_la_orden_de_reclamo(self, db_conn, orden_limpia, client):
        seed = orden_limpia
        servicio = _crear_servicio(db_conn, TALLER_A, 10)
        _agregar_detalle(db_conn, TALLER_A, seed.consecutivo_ot, servicio, seed.documento_usuario)
        # Entregada hace 20 días + 10 de garantía = venció hace 10 días.
        _entregar(db_conn, TALLER_A, seed.consecutivo_ot, date.today() - timedelta(days=20))

        resp = client.post(
            "/api/ordenes-trabajo",
            json={
                "placa_mot_ot": seed.placa_moto,
                "kilometraje_ingreso_ot": 15200,
                "cod_ot_est_ot": 6,
            },
            headers=auth_headers(TALLER_A),
        )

        assert resp.status_code == 400
        assert "venció" in resp.json()["message"]

    def test_garantia_vigente_permite_crear_la_orden_de_reclamo(self, db_conn, orden_limpia, client):
        seed = orden_limpia
        servicio = _crear_servicio(db_conn, TALLER_A, 10)
        _agregar_detalle(db_conn, TALLER_A, seed.consecutivo_ot, servicio, seed.documento_usuario)
        # Entregada hace 5 días + 10 de garantía = vigente 5 días más.
        _entregar(db_conn, TALLER_A, seed.consecutivo_ot, date.today() - timedelta(days=5))

        resp = client.post(
            "/api/ordenes-trabajo",
            json={
                "placa_mot_ot": seed.placa_moto,
                "kilometraje_ingreso_ot": 15200,
                "cod_ot_est_ot": 6,
            },
            headers=auth_headers(TALLER_A),
        )

        assert resp.status_code == 201
        consecutivo_creado = resp.json()["consecutivoOt"]

        with db_conn.cursor() as cur:
            cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(TALLER_A),))
            cur.execute(
                "DELETE FROM orden_estado_historial WHERE cod_taller = %s AND consecutivo_ot = %s",
                (TALLER_A, consecutivo_creado),
            )
            cur.execute(
                "DELETE FROM ordenes_trabajo WHERE cod_taller = %s AND consecutivo_ot = %s",
                (TALLER_A, consecutivo_creado),
            )
