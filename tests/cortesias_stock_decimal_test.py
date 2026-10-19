"""F1-06 + F1-03: el switch "¿Se factura?" se guardaba como cantidad_deto
NEGATIVA, y los triggers de inventario ignoraban cualquier línea con
cantidad_deto <= 0 -- un repuesto marcado como cortesía salía de la bodega
pero el inventario nunca bajaba (hueco de fraude). Además stock_pro y las
columnas de movimientos_inventario eran INTEGER aunque cantidad_deto ya
permitía decimales, así que los triggers truncaban (1.5 -> 1).

Estos tests van directo contra Postgres (sin pasar por el servicio) porque el
bug y el fix viven en los triggers, no en Python -- un mock de repositorio
nunca lo habría detectado."""
from decimal import Decimal

import psycopg
import pytest

from tests.conftest import TALLER_A

pytestmark = pytest.mark.db


@pytest.fixture
def producto_bien(db_conn, seed_talleres):
    """Producto BIEN propio (no el del seed compartido de módulo) con stock=100,
    para no interferir con otros tests que comparten seed_talleres."""
    seed = seed_talleres[TALLER_A]
    with db_conn.cursor() as cur:
        cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(TALLER_A),))
        cur.execute(
            "INSERT INTO productos (cod_taller, nombre_pro, stock_pro, stock_pro_min, "
            "cod_est_pro, precio_pro, tipo_pro) VALUES (%s, 'BIEN cortesias test', 100, 2, 1, 15000, 'BIEN') "
            "RETURNING cod_pro",
            (TALLER_A,),
        )
        cod_pro = cur.fetchone()[0]

    yield {
        "cod_taller": TALLER_A,
        "cod_pro": cod_pro,
        "consecutivo_ot": seed.consecutivo_ot,
        "documento_usu": seed.documento_usuario,
    }

    with db_conn.cursor() as cur:
        cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(TALLER_A),))
        cur.execute(
            "DELETE FROM detalle_orden_trabajo WHERE cod_taller=%s AND cod_pro_deto=%s",
            (TALLER_A, cod_pro),
        )
        cur.execute(
            "DELETE FROM movimientos_inventario WHERE cod_taller=%s AND cod_pro_mov=%s",
            (TALLER_A, cod_pro),
        )
        cur.execute("DELETE FROM productos WHERE cod_taller=%s AND cod_pro=%s", (TALLER_A, cod_pro))


def _insertar_detalle(db_conn, p, cantidad, cobrar=True, motivo=None):
    with db_conn.cursor() as cur:
        cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(p["cod_taller"]),))
        cur.execute(
            "INSERT INTO detalle_orden_trabajo (cod_taller, consecutivo_ot_deto, cod_pro_deto, "
            "fecha_confirmacion_deto, valor_unitario_deto, cantidad_deto, documento_usu_deto, "
            "cobrar_deto, motivo_no_cobro_deto) "
            "VALUES (%s, %s, %s, CURRENT_DATE, 15000, %s, %s, %s, %s)",
            (p["cod_taller"], p["consecutivo_ot"], p["cod_pro"], cantidad, p["documento_usu"], cobrar, motivo),
        )


def _stock(db_conn, p) -> Decimal:
    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT stock_pro FROM productos WHERE cod_taller=%s AND cod_pro=%s",
            (p["cod_taller"], p["cod_pro"]),
        )
        return cur.fetchone()[0]


def _ultimo_movimiento(db_conn, p):
    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT cantidad_mov, motivo_mov FROM movimientos_inventario "
            "WHERE cod_taller=%s AND cod_pro_mov=%s ORDER BY cod_mov DESC LIMIT 1",
            (p["cod_taller"], p["cod_pro"]),
        )
        return cur.fetchone()


def test_cortesia_descuenta_stock_y_queda_en_kardex(db_conn, producto_bien):
    """El bug original: una línea marcada como cortesía no bajaba el stock.
    Mutación que debe atraparlo: reintroducir un `IF NOT NEW.cobrar_deto THEN
    RETURN NEW` (o el `IF cantidad_deto <= 0` de antes) en fn_actualizar_stock."""
    _insertar_detalle(db_conn, producto_bien, Decimal("1"), cobrar=False, motivo="Cortesía de prueba")

    assert _stock(db_conn, producto_bien) == Decimal("99.000")
    cantidad_mov, motivo_mov = _ultimo_movimiento(db_conn, producto_bien)
    assert cantidad_mov == Decimal("-1.000")
    assert motivo_mov == f"Cortesía OT #{producto_bien['consecutivo_ot']}"


def test_cantidad_decimal_descuenta_exacto(db_conn, producto_bien):
    """Mutación que debe atraparlo: reintroducir `::integer` en el trigger de
    INSERT (truncaría 1.5 a 1, dejando el stock en 99 en vez de 98.5)."""
    _insertar_detalle(db_conn, producto_bien, Decimal("1.5"))

    assert _stock(db_conn, producto_bien) == Decimal("98.500")
    cantidad_mov, _ = _ultimo_movimiento(db_conn, producto_bien)
    assert cantidad_mov == Decimal("-1.500")


def test_editar_cantidad_ajusta_delta_decimal(db_conn, producto_bien):
    _insertar_detalle(db_conn, producto_bien, Decimal("1.5"))
    assert _stock(db_conn, producto_bien) == Decimal("98.500")

    with db_conn.cursor() as cur:
        cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(producto_bien["cod_taller"]),))
        cur.execute(
            "UPDATE detalle_orden_trabajo SET cantidad_deto = %s "
            "WHERE cod_taller=%s AND consecutivo_ot_deto=%s AND cod_pro_deto=%s",
            (Decimal("2.25"), producto_bien["cod_taller"], producto_bien["consecutivo_ot"], producto_bien["cod_pro"]),
        )

    # 98.5 - (2.25 - 1.5) = 97.75
    assert _stock(db_conn, producto_bien) == Decimal("97.750")
    cantidad_mov, motivo_mov = _ultimo_movimiento(db_conn, producto_bien)
    assert cantidad_mov == Decimal("-0.750")
    assert motivo_mov == "Edición de OT"


def test_eliminar_detalle_revierte_stock_decimal(db_conn, producto_bien):
    _insertar_detalle(db_conn, producto_bien, Decimal("1.5"))
    assert _stock(db_conn, producto_bien) == Decimal("98.500")

    with db_conn.cursor() as cur:
        cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(producto_bien["cod_taller"]),))
        cur.execute(
            "DELETE FROM detalle_orden_trabajo WHERE cod_taller=%s AND consecutivo_ot_deto=%s AND cod_pro_deto=%s",
            (producto_bien["cod_taller"], producto_bien["consecutivo_ot"], producto_bien["cod_pro"]),
        )

    assert _stock(db_conn, producto_bien) == Decimal("100.000")


def test_paquete_componente_decimal(db_conn, producto_bien):
    """Un paquete con un componente de 0.5 vendido con cantidad_deto=3 debe
    descontar exactamente 1.5 del componente (no 1 por truncado)."""
    p = producto_bien
    with db_conn.cursor() as cur:
        cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(p["cod_taller"]),))
        cur.execute(
            "INSERT INTO productos (cod_taller, nombre_pro, cod_est_pro, precio_pro, tipo_pro) "
            "VALUES (%s, 'Paquete cortesias test', 1, 50000, 'PAQUETE') RETURNING cod_pro",
            (p["cod_taller"],),
        )
        cod_paquete = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO paquete_componentes (cod_taller, cod_pro_paq, cod_pro_comp, cantidad_comp) "
            "VALUES (%s, %s, %s, %s)",
            (p["cod_taller"], cod_paquete, p["cod_pro"], Decimal("0.5")),
        )
        cur.execute(
            "INSERT INTO detalle_orden_trabajo (cod_taller, consecutivo_ot_deto, cod_pro_deto, "
            "fecha_confirmacion_deto, valor_unitario_deto, cantidad_deto, documento_usu_deto) "
            "VALUES (%s, %s, %s, CURRENT_DATE, 50000, 3, %s)",
            (p["cod_taller"], p["consecutivo_ot"], cod_paquete, p["documento_usu"]),
        )

    assert _stock(db_conn, p) == Decimal("98.500")

    with db_conn.cursor() as cur:
        cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(p["cod_taller"]),))
        cur.execute(
            "DELETE FROM detalle_orden_trabajo WHERE cod_taller=%s AND cod_pro_deto=%s",
            (p["cod_taller"], cod_paquete),
        )
        cur.execute(
            "DELETE FROM paquete_componentes WHERE cod_taller=%s AND cod_pro_paq=%s",
            (p["cod_taller"], cod_paquete),
        )
        cur.execute("DELETE FROM productos WHERE cod_taller=%s AND cod_pro=%s", (p["cod_taller"], cod_paquete))


def test_no_existen_cantidades_negativas(db_conn, producto_bien):
    """Mutación que debe atraparlo: quitar chk_deto_cantidad_positiva."""
    with pytest.raises(psycopg.errors.CheckViolation):
        _insertar_detalle(db_conn, producto_bien, Decimal("-1"))


def test_cobrar_false_sin_motivo_viola_check(db_conn, producto_bien):
    """Mutación que debe atraparlo: quitar chk_deto_motivo_si_no_cobra."""
    with pytest.raises(psycopg.errors.CheckViolation):
        _insertar_detalle(db_conn, producto_bien, Decimal("1"), cobrar=False, motivo=None)


def test_totales_sin_error_de_redondeo(db_conn, producto_bien):
    """3 líneas de 0.1 no deben arrastrar error de redondeo de punto flotante
    en vw_resumen_financiero_ot (que ahora filtra por cobrar_deto, no por signo)."""
    p = producto_bien
    for _ in range(3):
        with db_conn.cursor() as cur:
            cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(p["cod_taller"]),))
            cur.execute(
                "INSERT INTO detalle_orden_trabajo (cod_taller, consecutivo_ot_deto, cod_pro_deto, "
                "fecha_confirmacion_deto, valor_unitario_deto, cantidad_deto, documento_usu_deto) "
                "VALUES (%s, %s, %s, CURRENT_DATE, 10000, 0.1, %s)",
                (p["cod_taller"], p["consecutivo_ot"], p["cod_pro"], p["documento_usu"]),
            )

    with db_conn.cursor() as cur:
        cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(p["cod_taller"]),))
        cur.execute(
            "SELECT subtotal_productos FROM vw_resumen_financiero_ot WHERE consecutivo_ot=%s",
            (p["consecutivo_ot"],),
        )
        subtotal = cur.fetchone()[0]

    # La orden ya trae 1 línea del seed compartido (50000 * 1 = 50000); estas
    # 3 líneas de 0.1 suman 3 * 0.1 * 10000 = 3000 exactos. Con NUMERIC no hay
    # el arrastre de redondeo de punto flotante que 3 * 0.1 produce en binario.
    assert Decimal(str(subtotal)) == Decimal("53000")
