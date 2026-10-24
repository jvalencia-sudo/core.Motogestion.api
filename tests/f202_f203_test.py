"""F2-02 (retiro de ítems con motivo, diagnóstico, historial de estados con
hora real, rate limit de los endpoints públicos) y F2-03 (aprobación de
cotización, opcional por taller). Cada test crea su propia orden/producto --
no toca el seed compartido del módulo (seed_talleres)."""
import pytest

from tests.conftest import TALLER_A, auth_headers

pytestmark = [pytest.mark.db, pytest.mark.usefixtures("mock_auth0")]


def _crear_producto(db_conn, stock=50, precio=40000):
    with db_conn.cursor() as cur:
        cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(TALLER_A),))
        cur.execute(
            "INSERT INTO productos (cod_taller, nombre_pro, stock_pro, stock_pro_min, "
            "cod_est_pro, precio_pro, tipo_pro) VALUES (%s, 'Producto F2-02 test', %s, 2, 1, %s, 'BIEN') "
            "RETURNING cod_pro",
            (TALLER_A, stock, precio),
        )
        return cur.fetchone()[0]


def _stock(db_conn, cod_pro):
    with db_conn.cursor() as cur:
        cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(TALLER_A),))
        cur.execute("SELECT stock_pro FROM productos WHERE cod_taller=%s AND cod_pro=%s", (TALLER_A, cod_pro))
        return cur.fetchone()[0]


def _limpiar(db_conn, consecutivo_ot, cod_pro):
    with db_conn.cursor() as cur:
        cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(TALLER_A),))
        cur.execute(
            "DELETE FROM orden_aprobacion_cotizacion WHERE cod_taller=%s AND consecutivo_ot=%s",
            (TALLER_A, consecutivo_ot),
        )
        cur.execute(
            "DELETE FROM orden_estado_historial WHERE cod_taller=%s AND consecutivo_ot=%s",
            (TALLER_A, consecutivo_ot),
        )
        cur.execute(
            "DELETE FROM detalle_orden_trabajo WHERE cod_taller=%s AND consecutivo_ot_deto=%s",
            (TALLER_A, consecutivo_ot),
        )
        cur.execute(
            "DELETE FROM ordenes_trabajo WHERE cod_taller=%s AND consecutivo_ot=%s",
            (TALLER_A, consecutivo_ot),
        )
        cur.execute("DELETE FROM movimientos_inventario WHERE cod_taller=%s AND cod_pro_mov=%s", (TALLER_A, cod_pro))
        cur.execute("DELETE FROM productos WHERE cod_taller=%s AND cod_pro=%s", (TALLER_A, cod_pro))


@pytest.fixture
def orden_con_item(client, db_conn, seed_talleres):
    seed = seed_talleres[TALLER_A]
    cod_pro = _crear_producto(db_conn)
    resp = client.post(
        "/api/ordenes-trabajo",
        json={
            "placa_mot_ot": seed.placa_moto,
            "kilometraje_ingreso_ot": 12000,
            "detalles": [{"cod_pro_deto": cod_pro, "cantidad_deto": 1}],
        },
        headers=auth_headers(TALLER_A),
    )
    assert resp.status_code == 201, resp.text
    consecutivo_ot = resp.json()["consecutivoOt"]
    yield consecutivo_ot, cod_pro
    _limpiar(db_conn, consecutivo_ot, cod_pro)


def _toggle_aprobacion(db_conn, encender: bool):
    with db_conn.cursor() as cur:
        cur.execute(
            "UPDATE talleres SET exige_aprobacion_cotizacion_tal = %s WHERE cod_taller = %s",
            (encender, TALLER_A),
        )


def _token_de(client, consecutivo_ot: int) -> str:
    resp = client.get(f"/api/ordenes-trabajo/{consecutivo_ot}", headers=auth_headers(TALLER_A))
    assert resp.status_code == 200
    return resp.json()["tokenPublico"]


class TestRetirarProducto:
    def test_requiere_motivo(self, client, orden_con_item):
        consecutivo_ot, cod_pro = orden_con_item
        resp = client.patch(
            f"/api/ordenes-trabajo/{consecutivo_ot}/productos/{cod_pro}/retirar",
            json={},
            headers=auth_headers(TALLER_A),
        )
        assert resp.status_code == 422

    def test_retirar_devuelve_stock_y_excluye_el_monto_pero_sigue_visible(
        self, client, db_conn, orden_con_item
    ):
        consecutivo_ot, cod_pro = orden_con_item
        assert _stock(db_conn, cod_pro) == 49  # 50 - 1 al crear la orden

        resp = client.patch(
            f"/api/ordenes-trabajo/{consecutivo_ot}/productos/{cod_pro}/retirar",
            json={"motivo": "No fue necesario"},
            headers=auth_headers(TALLER_A),
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["totalOt"] == 0.0
        [detalle] = data["detalles"]
        assert detalle["retirado"] is True
        assert detalle["motivoRetiro"] == "No fue necesario"

        assert _stock(db_conn, cod_pro) == 50  # devuelto

    def test_retirar_dos_veces_el_mismo_item_da_404_y_no_duplica_la_devolucion(
        self, client, db_conn, orden_con_item
    ):
        consecutivo_ot, cod_pro = orden_con_item
        primero = client.patch(
            f"/api/ordenes-trabajo/{consecutivo_ot}/productos/{cod_pro}/retirar",
            json={"motivo": "No fue necesario"},
            headers=auth_headers(TALLER_A),
        )
        assert primero.status_code == 200
        assert _stock(db_conn, cod_pro) == 50

        segundo = client.patch(
            f"/api/ordenes-trabajo/{consecutivo_ot}/productos/{cod_pro}/retirar",
            json={"motivo": "Otra vez"},
            headers=auth_headers(TALLER_A),
        )
        assert segundo.status_code == 404
        assert _stock(db_conn, cod_pro) == 50  # no se devolvió una segunda vez


class TestDiagnostico:
    def test_guardar_diagnostico_se_refleja_en_la_orden(self, client, orden_con_item):
        consecutivo_ot, _ = orden_con_item
        resp = client.patch(
            f"/api/ordenes-trabajo/{consecutivo_ot}/diagnostico",
            json={"texto": "Pastillas de freno al 10%"},
            headers=auth_headers(TALLER_A),
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["diagnosticoOt"] == "Pastillas de freno al 10%"


class TestHistorialDeEstados:
    def test_cambiar_de_estado_registra_un_hito_con_hora_real(self, client, db_conn, orden_con_item):
        consecutivo_ot, _ = orden_con_item
        resp = client.patch(
            f"/api/ordenes-trabajo/{consecutivo_ot}/estado",
            json={"cod_ot_est_ot": 2},
            headers=auth_headers(TALLER_A),
        )
        assert resp.status_code == 200

        with db_conn.cursor() as cur:
            cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(TALLER_A),))
            cur.execute(
                "SELECT cod_ot_est_ot FROM orden_estado_historial "
                "WHERE cod_taller=%s AND consecutivo_ot=%s ORDER BY ocurrido_en",
                (TALLER_A, consecutivo_ot),
            )
            hitos = [row[0] for row in cur.fetchall()]
        assert hitos == [1, 2]  # creada en Pendiente, luego En Proceso


class TestAprobacionCotizacion:
    def test_409_si_el_taller_no_exige_aprobacion(self, client, db_conn, orden_con_item):
        consecutivo_ot, _ = orden_con_item
        _toggle_aprobacion(db_conn, False)
        client.patch(
            f"/api/ordenes-trabajo/{consecutivo_ot}/estado",
            json={"cod_ot_est_ot": 2},
            headers=auth_headers(TALLER_A),
        )
        token = _token_de(client, consecutivo_ot)

        resp = client.patch(f"/api/public/ordenes-trabajo/{token}/aprobar")
        assert resp.status_code == 409

    def test_flujo_completo_aprobar_es_idempotente_y_se_invalida_si_cambia_la_cotizacion(
        self, client, db_conn, orden_con_item
    ):
        consecutivo_ot, cod_pro = orden_con_item
        try:
            _toggle_aprobacion(db_conn, True)
            client.patch(
                f"/api/ordenes-trabajo/{consecutivo_ot}/estado",
                json={"cod_ot_est_ot": 2},
                headers=auth_headers(TALLER_A),
            )
            token = _token_de(client, consecutivo_ot)

            publico_antes = client.get(f"/api/public/ordenes-trabajo/estado/{token}")
            assert publico_antes.status_code == 200
            assert publico_antes.json()["esperandoAprobacion"] is True

            aprobar_1 = client.patch(f"/api/public/ordenes-trabajo/{token}/aprobar")
            assert aprobar_1.status_code == 200, aprobar_1.text
            aprobado_en_1 = aprobar_1.json()["aprobadoEn"]

            # Idempotente: una segunda aprobación no duplica fila ni cambia la hora.
            aprobar_2 = client.patch(f"/api/public/ordenes-trabajo/{token}/aprobar")
            assert aprobar_2.status_code == 200
            assert aprobar_2.json()["aprobadoEn"] == aprobado_en_1

            with db_conn.cursor() as cur:
                cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(TALLER_A),))
                cur.execute(
                    "SELECT count(*) FROM orden_aprobacion_cotizacion WHERE cod_taller=%s AND consecutivo_ot=%s",
                    (TALLER_A, consecutivo_ot),
                )
                assert cur.fetchone()[0] == 1

            publico_despues = client.get(f"/api/public/ordenes-trabajo/estado/{token}")
            assert publico_despues.json()["esperandoAprobacion"] is False
            assert publico_despues.json()["aprobadoEn"] is not None

            # Retirar un ítem cambia la cotización -> invalida la aprobación vigente.
            retiro = client.patch(
                f"/api/ordenes-trabajo/{consecutivo_ot}/productos/{cod_pro}/retirar",
                json={"motivo": "Se dañó al pedirlo"},
                headers=auth_headers(TALLER_A),
            )
            assert retiro.status_code == 200

            with db_conn.cursor() as cur:
                cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(TALLER_A),))
                cur.execute(
                    "SELECT vigente FROM orden_aprobacion_cotizacion WHERE cod_taller=%s AND consecutivo_ot=%s",
                    (TALLER_A, consecutivo_ot),
                )
                assert cur.fetchone()[0] is False
        finally:
            _toggle_aprobacion(db_conn, False)


class TestRateLimitPublico:
    def test_get_estado_publico_responde_429_al_superar_el_limite(self, client, orden_con_item):
        consecutivo_ot, _ = orden_con_item
        token = _token_de(client, consecutivo_ot)

        respuestas = [client.get(f"/api/public/ordenes-trabajo/estado/{token}") for _ in range(31)]
        assert respuestas[-1].status_code == 429
        assert all(r.status_code == 200 for r in respuestas[:30])
