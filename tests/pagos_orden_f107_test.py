"""F1-07: pagos y abonos por orden -- nueva tabla pagos_orden, CON RLS a
diferencia de `pagos` (billing de la plataforma vía Wompi, sin RLS a
propósito). Cubre los criterios de aceptación: varios abonos a una orden,
el saldo se actualiza excluyendo ítems no cobrados, y el listado expone
saldo_ot (para el filtro "con saldo pendiente" del front). La cobertura de
RLS de pagos_orden (F0-02) es automática -- ver tests/rls_coverage_test.py,
no necesita cambios."""
from unittest.mock import patch

import pytest

from domain.models.auth.user_model import UserPermissionsModel
from tests.conftest import TALLER_A, _SUB_POR_TOKEN, auth_headers

pytestmark = [pytest.mark.db, pytest.mark.usefixtures("mock_auth0")]

MECANICO_TOKEN = "test-token-taller-a-mecanico-f107"
MECANICO_SUB = "test|taller-a-mecanico-f107"
MECANICO_DOCUMENTO = "900100499"
PERMISOS_BASE_MECANICO = ["ver:ordenes-trabajo", "crear_editar:ordenes-trabajo"]


@pytest.fixture
def orden_limpia(db_conn, seed_talleres):
    """La orden sembrada (estado Pendiente, 1 ítem BIEN cantidad=1 a 50000),
    sin pagos ni ítems extra, antes y después de cada test -- seed_talleres
    es scope=module, un test no debe dejarle saldo/pagos al siguiente."""
    seed = seed_talleres[TALLER_A]

    def _limpiar():
        with db_conn.cursor() as cur:
            cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(TALLER_A),))
            cur.execute(
                "DELETE FROM pagos_orden WHERE cod_taller = %s AND consecutivo_ot_pago = %s",
                (TALLER_A, seed.consecutivo_ot),
            )
            cur.execute(
                "DELETE FROM detalle_orden_trabajo WHERE cod_taller = %s "
                "AND consecutivo_ot_deto = %s AND cod_pro_deto != %s",
                (TALLER_A, seed.consecutivo_ot, seed.cod_producto),
            )
            cur.execute(
                "UPDATE ordenes_trabajo SET cod_ot_est_ot = 1 "
                "WHERE cod_taller = %s AND consecutivo_ot = %s",
                (TALLER_A, seed.consecutivo_ot),
            )

    _limpiar()
    yield seed
    _limpiar()


def _registrar_pago(client, consecutivo_ot, valor, metodo="EFECTIVO", headers=None, **overrides):
    payload = {"valorPago": valor, "metodoPago": metodo}
    payload.update(overrides)
    return client.post(
        f"/api/ordenes-trabajo/{consecutivo_ot}/pagos",
        json=payload,
        headers=headers or auth_headers(TALLER_A),
    )


def _obtener_orden(client, consecutivo_ot):
    resp = client.get(f"/api/ordenes-trabajo/{consecutivo_ot}", headers=auth_headers(TALLER_A))
    assert resp.status_code == 200
    return resp.json()


def _crear_servicio(db_conn, cod_taller: int, precio: int) -> int:
    with db_conn.cursor() as cur:
        cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(cod_taller),))
        cur.execute(
            "INSERT INTO productos (cod_taller, nombre_pro, cod_est_pro, precio_pro, tipo_pro) "
            "VALUES (%s, 'Servicio de prueba F1-07', 1, %s, 'SERVICIO') RETURNING cod_pro",
            (cod_taller, precio),
        )
        return cur.fetchone()[0]


class TestVariosAbonosActualizanSaldo:
    def test_se_pueden_registrar_varios_abonos_y_el_saldo_se_actualiza(self, client, orden_limpia):
        seed = orden_limpia
        orden = _obtener_orden(client, seed.consecutivo_ot)
        assert orden["totalOt"] == 50000
        assert orden["totalPagado"] == 0
        assert orden["saldoOt"] == 50000

        resp1 = _registrar_pago(client, seed.consecutivo_ot, 20000)
        assert resp1.status_code == 201
        assert resp1.json()["anuladoPago"] is False

        resp2 = _registrar_pago(
            client, seed.consecutivo_ot, 15000,
            metodo="TRANSFERENCIA", referenciaPago="TRX-001",
        )
        assert resp2.status_code == 201

        orden = _obtener_orden(client, seed.consecutivo_ot)
        assert orden["totalPagado"] == 35000
        assert orden["saldoOt"] == 15000

        pagos = client.get(
            f"/api/ordenes-trabajo/{seed.consecutivo_ot}/pagos", headers=auth_headers(TALLER_A)
        )
        assert pagos.status_code == 200
        assert len(pagos.json()) == 2

    def test_anular_un_pago_revierte_el_saldo(self, client, orden_limpia):
        seed = orden_limpia
        resp = _registrar_pago(client, seed.consecutivo_ot, 20000)
        cod_pago = resp.json()["codPagoOrden"]
        assert _obtener_orden(client, seed.consecutivo_ot)["saldoOt"] == 30000

        anular = client.patch(
            f"/api/ordenes-trabajo/{seed.consecutivo_ot}/pagos/{cod_pago}/anular",
            json={"motivo": "Pago duplicado por error"},
            headers=auth_headers(TALLER_A),
        )
        assert anular.status_code == 200
        assert anular.json()["anuladoPago"] is True

        # Vuelve a quedar como si no se hubiera pagado.
        assert _obtener_orden(client, seed.consecutivo_ot)["saldoOt"] == 50000

    def test_no_se_puede_anular_un_pago_ya_anulado(self, client, orden_limpia):
        seed = orden_limpia
        resp = _registrar_pago(client, seed.consecutivo_ot, 10000)
        cod_pago = resp.json()["codPagoOrden"]

        primera = client.patch(
            f"/api/ordenes-trabajo/{seed.consecutivo_ot}/pagos/{cod_pago}/anular",
            json={"motivo": "Error de digitación"},
            headers=auth_headers(TALLER_A),
        )
        assert primera.status_code == 200

        segunda = client.patch(
            f"/api/ordenes-trabajo/{seed.consecutivo_ot}/pagos/{cod_pago}/anular",
            json={"motivo": "Intento repetido"},
            headers=auth_headers(TALLER_A),
        )
        assert segunda.status_code == 400

    def test_no_se_puede_registrar_pago_a_orden_anulada(self, client, db_conn, orden_limpia):
        seed = orden_limpia
        with db_conn.cursor() as cur:
            cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(TALLER_A),))
            cur.execute(
                "UPDATE ordenes_trabajo SET cod_ot_est_ot = 5 "
                "WHERE cod_taller = %s AND consecutivo_ot = %s",
                (TALLER_A, seed.consecutivo_ot),
            )

        resp = _registrar_pago(client, seed.consecutivo_ot, 10000)
        assert resp.status_code == 400


class TestSaldoExcluyeItemsNoCobrados:
    def test_un_item_de_cortesia_no_cuenta_para_el_saldo(self, client, db_conn, orden_limpia):
        seed = orden_limpia
        servicio = _crear_servicio(db_conn, TALLER_A, 30000)

        agregar = client.post(
            f"/api/ordenes-trabajo/{seed.consecutivo_ot}/productos",
            json={
                "codProDeto": servicio,
                "cantidadDeto": 1,
                "cobrarDeto": False,
                "motivoNoCobroDeto": "Cortesía por reclamo anterior",
            },
            headers=auth_headers(TALLER_A),
        )
        assert agregar.status_code == 200

        # El total sigue siendo 50000 (el del BIEN del seed): el ítem de
        # cortesía (cobrar_deto=false) no se suma al total cobrable.
        orden = _obtener_orden(client, seed.consecutivo_ot)
        assert orden["totalOt"] == 50000
        assert orden["saldoOt"] == 50000

        _registrar_pago(client, seed.consecutivo_ot, 50000)
        assert _obtener_orden(client, seed.consecutivo_ot)["saldoOt"] == 0


class TestEntregarConSaldoPendiente:
    @pytest.fixture
    def orden_finalizada(self, db_conn, orden_limpia):
        seed = orden_limpia
        with db_conn.cursor() as cur:
            cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(TALLER_A),))
            cur.execute(
                "UPDATE ordenes_trabajo SET cod_ot_est_ot = 3 "
                "WHERE cod_taller = %s AND consecutivo_ot = %s",
                (TALLER_A, seed.consecutivo_ot),
            )
        return seed

    def test_entregar_con_saldo_pendiente_sin_confirmar_se_rechaza(self, client, orden_finalizada):
        resp = client.patch(
            f"/api/ordenes-trabajo/{orden_finalizada.consecutivo_ot}/entregar",
            json={},
            headers=auth_headers(TALLER_A),
        )
        assert resp.status_code == 400
        assert "saldo pendiente" in resp.json()["message"]

    def test_entregar_con_saldo_pendiente_confirmando_credito_funciona(self, client, orden_finalizada):
        resp = client.patch(
            f"/api/ordenes-trabajo/{orden_finalizada.consecutivo_ot}/entregar",
            json={"confirmarCredito": True},
            headers=auth_headers(TALLER_A),
        )
        assert resp.status_code == 200
        assert resp.json()["codOtEstOt"] == 4

    def test_entregar_sin_saldo_pendiente_no_exige_confirmar(self, client, orden_finalizada):
        _registrar_pago(client, orden_finalizada.consecutivo_ot, 50000)
        resp = client.patch(
            f"/api/ordenes-trabajo/{orden_finalizada.consecutivo_ot}/entregar",
            json={},
            headers=auth_headers(TALLER_A),
        )
        assert resp.status_code == 200

    def test_mover_a_entregada_por_patch_estado_tambien_exige_confirmar(self, client, orden_finalizada):
        """El tablero (arrastrar y soltar) mueve una orden a Entregada vía
        PATCH .../estado, NO vía el endpoint dedicado /entregar -- la
        confirmación de crédito tiene que vivir también en ese camino, o
        nunca se dispara en la UI real."""
        resp = client.patch(
            f"/api/ordenes-trabajo/{orden_finalizada.consecutivo_ot}/estado",
            json={"codOtEstOt": 4},
            headers=auth_headers(TALLER_A),
        )
        assert resp.status_code == 400
        assert "saldo pendiente" in resp.json()["message"]

        resp_confirmado = client.patch(
            f"/api/ordenes-trabajo/{orden_finalizada.consecutivo_ot}/estado",
            json={"codOtEstOt": 4, "confirmarCredito": True},
            headers=auth_headers(TALLER_A),
        )
        assert resp_confirmado.status_code == 200
        assert resp_confirmado.json()["codOtEstOt"] == 4

    def test_arrastrar_en_el_tablero_a_entregada_tambien_exige_confirmar(self, client, orden_finalizada):
        """Esta es la ruta que la UI real usa hoy (arrastrar y soltar en el
        tablero, PUT /api/tablero/.../estado) -- no el endpoint dedicado
        /entregar ni el PATCH .../estado de ordenes-trabajo."""
        resp = client.put(
            f"/api/tablero/{orden_finalizada.consecutivo_ot}/estado",
            json={"codEstado": 4},
            headers=auth_headers(TALLER_A),
        )
        assert resp.status_code == 400
        assert "saldo pendiente" in resp.json()["message"]

        resp_confirmado = client.put(
            f"/api/tablero/{orden_finalizada.consecutivo_ot}/estado",
            json={"codEstado": 4, "confirmarCredito": True},
            headers=auth_headers(TALLER_A),
        )
        assert resp_confirmado.status_code == 200


@pytest.fixture
def mecanico_headers(db_conn, seed_talleres):
    """Mecánico real en TALLER_A con los permisos normales de órdenes, pero
    SIN ningún permiso del módulo pagos-orden -- igual patrón que
    anular_orden_f105_test.py::mecanico_headers."""
    cod_taller = TALLER_A
    with db_conn.cursor() as cur:
        cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(cod_taller),))
        cur.execute(
            "INSERT INTO perfiles (cod_taller, es_admin, cod_est_prf, nombre_prf) "
            "VALUES (%s, false, 1, 'Mecanico F1-07 test') RETURNING cod_prf",
            (cod_taller,),
        )
        cod_prf = cur.fetchone()[0]

        cur.execute(
            "INSERT INTO usuarios (cod_taller, documento_usu, nombre_usu, apellido_1_usu, "
            "correo_usu, contrasena_usu, cod_tipo_usu, cod_est_usu, sub_id_usu, "
            "cod_prf_usu, es_admin_usu) "
            "VALUES (%s, %s, 'Mecanico', 'F1-07', %s, 'test', 1, 1, %s, %s, false)",
            (cod_taller, MECANICO_DOCUMENTO, "mecanico-f107@test.local", MECANICO_SUB, cod_prf),
        )

        cur.execute(
            "SELECT cod_prm FROM permisos WHERE nombre_prm = ANY(%s)",
            (PERMISOS_BASE_MECANICO,),
        )
        cods_prm = [row[0] for row in cur.fetchall()]
        assert len(cods_prm) == len(PERMISOS_BASE_MECANICO)
        for cod_prm in cods_prm:
            cur.execute(
                "INSERT INTO perfiles_permisos (cod_taller, cod_prm_pp, cod_prf_pp, cod_est_pp) "
                "VALUES (%s, %s, %s, 1)",
                (cod_taller, cod_prm, cod_prf),
            )

    async def _verify(self, token: str) -> UserPermissionsModel:
        if token == MECANICO_TOKEN:
            return UserPermissionsModel(user_id=MECANICO_SUB, permissions=["*"])
        sub = _SUB_POR_TOKEN.get(token)
        if sub is None:
            raise ValueError(f"Token de test desconocido: {token!r}")
        return UserPermissionsModel(user_id=sub, permissions=["*"])

    with patch(
        "infrastructure.providers.auth.auth0_provider.Auth0Provider.verify",
        new=_verify,
    ):
        yield {"Authorization": f"Bearer {MECANICO_TOKEN}"}

    with db_conn.cursor() as cur:
        cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(cod_taller),))
        cur.execute(
            "DELETE FROM perfiles_permisos WHERE cod_taller = %s AND cod_prf_pp = %s",
            (cod_taller, cod_prf),
        )
        cur.execute("DELETE FROM usuarios WHERE documento_usu = %s", (MECANICO_DOCUMENTO,))
        cur.execute("DELETE FROM perfiles WHERE cod_taller = %s AND cod_prf = %s", (cod_taller, cod_prf))


class TestPermisosDePagos:
    def test_registrar_pago_sin_permiso_es_403(self, client, orden_limpia, mecanico_headers):
        resp = _registrar_pago(client, orden_limpia.consecutivo_ot, 10000, headers=mecanico_headers)
        assert resp.status_code == 403

    def test_anular_pago_sin_permiso_es_403(self, client, orden_limpia, mecanico_headers):
        resp = _registrar_pago(client, orden_limpia.consecutivo_ot, 10000)
        cod_pago = resp.json()["codPagoOrden"]

        anular = client.patch(
            f"/api/ordenes-trabajo/{orden_limpia.consecutivo_ot}/pagos/{cod_pago}/anular",
            json={"motivo": "Intento sin permiso"},
            headers=mecanico_headers,
        )
        assert anular.status_code == 403

    def test_ver_pagos_sin_permiso_es_403(self, client, orden_limpia, mecanico_headers):
        resp = client.get(
            f"/api/ordenes-trabajo/{orden_limpia.consecutivo_ot}/pagos", headers=mecanico_headers
        )
        assert resp.status_code == 403
