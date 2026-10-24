"""F1-05: anular una orden ya no es "pasarla a Cancelada sin dejar rastro" --
ahora exige motivo, un permiso propio (anular:ordenes-trabajo), devuelve al
inventario los bienes de la orden con un movimiento ENTRADA (sin borrar el
detalle, que queda como historial) y deja constancia de quién/cuándo. Cubre
también el bloqueo de edición de ítems en una orden ya Entregada/Anulada y
el cierre de las 2 vías paralelas que antes dejaban llegar a "Anulada" (5)
sin pasar por este endpoint."""
from unittest.mock import patch

import pytest

from domain.models.auth.user_model import UserPermissionsModel
from tests.conftest import TALLER_A, _SUB_POR_TOKEN, auth_headers

pytestmark = [pytest.mark.db, pytest.mark.usefixtures("mock_auth0")]

MECANICO_TOKEN = "test-token-taller-a-mecanico-f105"
MECANICO_SUB = "test|taller-a-mecanico-f105"
MECANICO_DOCUMENTO = "900100399"

PERMISOS_BASE_MECANICO = ["ver:ordenes-trabajo", "crear_editar:ordenes-trabajo"]


@pytest.fixture
def orden_pendiente(db_conn, seed_talleres):
    """La orden sembrada por seed_talleres (con su único detalle BIEN
    cantidad=1) vuelve a Pendiente antes de cada test -- anular es terminal,
    cada test necesita partir de un estado limpio sin importar en qué quedó
    el test anterior de este módulo."""
    seed = seed_talleres[TALLER_A]
    with db_conn.cursor() as cur:
        cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(TALLER_A),))
        cur.execute(
            "UPDATE ordenes_trabajo SET cod_ot_est_ot = 1, motivo_anulacion_ot = NULL, "
            "fecha_anulacion_ot = NULL, documento_usu_anulacion_ot = NULL "
            "WHERE cod_taller = %s AND consecutivo_ot = %s",
            (TALLER_A, seed.consecutivo_ot),
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
    yield seed
    with db_conn.cursor() as cur:
        cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(TALLER_A),))
        cur.execute(
            "DELETE FROM movimientos_inventario WHERE cod_taller = %s AND motivo_mov LIKE 'Anulaci%%n OT %%'",
            (TALLER_A,),
        )


@pytest.fixture
def mecanico_headers(db_conn, seed_talleres):
    """Mecánico real en TALLER_A con los permisos normales de órdenes de
    trabajo, pero SIN anular:ordenes-trabajo."""
    cod_taller = TALLER_A
    with db_conn.cursor() as cur:
        cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(cod_taller),))
        cur.execute(
            "INSERT INTO perfiles (cod_taller, es_admin, cod_est_prf, nombre_prf) "
            "VALUES (%s, false, 1, 'Mecanico F1-05 test') RETURNING cod_prf",
            (cod_taller,),
        )
        cod_prf = cur.fetchone()[0]

        cur.execute(
            "INSERT INTO usuarios (cod_taller, documento_usu, nombre_usu, apellido_1_usu, "
            "correo_usu, contrasena_usu, cod_tipo_usu, cod_est_usu, sub_id_usu, "
            "cod_prf_usu, es_admin_usu) "
            "VALUES (%s, %s, 'Mecanico', 'F1-05', %s, 'test', 1, 1, %s, %s, false)",
            (cod_taller, MECANICO_DOCUMENTO, "mecanico-f105@test.local", MECANICO_SUB, cod_prf),
        )

        cur.execute(
            "SELECT cod_prm FROM permisos WHERE nombre_prm = ANY(%s)",
            (PERMISOS_BASE_MECANICO,),
        )
        cods_prm = [row[0] for row in cur.fetchall()]
        assert len(cods_prm) == len(PERMISOS_BASE_MECANICO), (
            "El catálogo de permisos no tiene alguno de los nombres esperados."
        )
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


def _stock_actual(db_conn, cod_pro):
    with db_conn.cursor() as cur:
        cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(TALLER_A),))
        cur.execute("SELECT stock_pro FROM productos WHERE cod_taller = %s AND cod_pro = %s", (TALLER_A, cod_pro))
        return cur.fetchone()[0]


class TestAnularDevuelveStockYAuditoria:
    def test_anula_devuelve_stock_con_entrada_y_no_borra_el_detalle(self, client, db_conn, orden_pendiente):
        seed = orden_pendiente
        stock_antes = _stock_actual(db_conn, seed.cod_producto)

        resp = client.patch(
            f"/api/ordenes-trabajo/{seed.consecutivo_ot}/anular",
            json={"motivo": "Cliente desistió del servicio"},
            headers=auth_headers(TALLER_A),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["codOtEstOt"] == 5
        assert data["motivoAnulacionOt"] == "Cliente desistió del servicio"
        assert data["documentoUsuAnulacionOt"] == seed.documento_usuario
        assert data["fechaAnulacionOt"] is not None

        stock_despues = _stock_actual(db_conn, seed.cod_producto)
        assert float(stock_despues) == float(stock_antes) + 1  # cantidad_deto=1 del seed

        with db_conn.cursor() as cur:
            cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(TALLER_A),))
            cur.execute(
                "SELECT tipo_mov, cantidad_mov, motivo_mov FROM movimientos_inventario "
                "WHERE cod_taller = %s AND cod_pro_mov = %s ORDER BY cod_mov DESC LIMIT 1",
                (TALLER_A, seed.cod_producto),
            )
            tipo, cantidad, motivo = cur.fetchone()
            assert tipo == "ENTRADA"
            assert float(cantidad) == 1.0
            assert motivo == f"Anulación OT #{seed.consecutivo_ot}"

            cur.execute(
                "SELECT count(*) FROM detalle_orden_trabajo "
                "WHERE cod_taller = %s AND consecutivo_ot_deto = %s",
                (TALLER_A, seed.consecutivo_ot),
            )
            assert cur.fetchone()[0] == 1  # el detalle NO se borró, queda como historial

    def test_no_se_puede_anular_una_orden_ya_anulada(self, client, orden_pendiente):
        seed = orden_pendiente
        primera = client.patch(
            f"/api/ordenes-trabajo/{seed.consecutivo_ot}/anular",
            json={"motivo": "Motivo válido"},
            headers=auth_headers(TALLER_A),
        )
        assert primera.status_code == 200

        segunda = client.patch(
            f"/api/ordenes-trabajo/{seed.consecutivo_ot}/anular",
            json={"motivo": "Otro motivo"},
            headers=auth_headers(TALLER_A),
        )
        assert segunda.status_code == 400

    def test_anular_sin_motivo_es_422(self, client, orden_pendiente):
        resp = client.patch(
            f"/api/ordenes-trabajo/{orden_pendiente.consecutivo_ot}/anular",
            json={},
            headers=auth_headers(TALLER_A),
        )
        assert resp.status_code == 422


def test_sin_permiso_no_puede_anular(client, orden_pendiente, mecanico_headers):
    resp = client.patch(
        f"/api/ordenes-trabajo/{orden_pendiente.consecutivo_ot}/anular",
        json={"motivo": "Motivo válido"},
        headers=mecanico_headers,
    )
    assert resp.status_code == 403


class TestOrdenEntregadaOAnuladaNoSeEdita:
    def test_no_se_puede_agregar_producto_a_orden_anulada(self, client, orden_pendiente):
        seed = orden_pendiente
        anular = client.patch(
            f"/api/ordenes-trabajo/{seed.consecutivo_ot}/anular",
            json={"motivo": "Motivo válido"},
            headers=auth_headers(TALLER_A),
        )
        assert anular.status_code == 200

        resp = client.post(
            f"/api/ordenes-trabajo/{seed.consecutivo_ot}/productos",
            json={"codProDeto": seed.cod_producto, "cantidadDeto": 1},
            headers=auth_headers(TALLER_A),
        )
        assert resp.status_code == 400

    def test_no_se_puede_quitar_producto_de_orden_anulada(self, client, orden_pendiente):
        seed = orden_pendiente
        anular = client.patch(
            f"/api/ordenes-trabajo/{seed.consecutivo_ot}/anular",
            json={"motivo": "Motivo válido"},
            headers=auth_headers(TALLER_A),
        )
        assert anular.status_code == 200

        resp = client.patch(
            f"/api/ordenes-trabajo/{seed.consecutivo_ot}/productos/{seed.cod_producto}/retirar",
            json={"motivo": "Motivo válido"},
            headers=auth_headers(TALLER_A),
        )
        assert resp.status_code == 400

    def test_no_se_puede_cambiar_cantidad_en_orden_entregada(self, client, db_conn, orden_pendiente):
        seed = orden_pendiente
        with db_conn.cursor() as cur:
            cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(TALLER_A),))
            cur.execute(
                "UPDATE ordenes_trabajo SET cod_ot_est_ot = 4 WHERE cod_taller = %s AND consecutivo_ot = %s",
                (TALLER_A, seed.consecutivo_ot),
            )

        resp = client.patch(
            f"/api/ordenes-trabajo/{seed.consecutivo_ot}/productos/{seed.cod_producto}",
            json={"cantidadDeto": 2},
            headers=auth_headers(TALLER_A),
        )
        assert resp.status_code == 400


def test_fn_audit_registra_el_documento_real_del_usuario_no_mt_app(client, db_conn, orden_pendiente):
    """F1-05: audit_log.usuario debe traer el documento real de quien anuló,
    no el rol de conexión de la app (mt_app) ni un session_user genérico."""
    seed = orden_pendiente
    resp = client.patch(
        f"/api/ordenes-trabajo/{seed.consecutivo_ot}/anular",
        json={"motivo": "Motivo válido para auditoría"},
        headers=auth_headers(TALLER_A),
    )
    assert resp.status_code == 200

    with db_conn.cursor() as cur:
        cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(TALLER_A),))
        cur.execute(
            "SELECT usuario FROM audit_log WHERE cod_taller = %s AND tabla = 'ordenes_trabajo' "
            "AND evento = 'U' AND (valor_nuevo->>'consecutivo_ot')::int = %s "
            "ORDER BY id DESC LIMIT 1",
            (TALLER_A, seed.consecutivo_ot),
        )
        row = cur.fetchone()
        assert row is not None
        assert row[0] == seed.documento_usuario


class TestHistorialDeCambios:
    def test_historial_incluye_el_evento_de_anulacion(self, client, orden_pendiente):
        seed = orden_pendiente
        anular = client.patch(
            f"/api/ordenes-trabajo/{seed.consecutivo_ot}/anular",
            json={"motivo": "Motivo válido para historial"},
            headers=auth_headers(TALLER_A),
        )
        assert anular.status_code == 200

        resp = client.get(
            f"/api/ordenes-trabajo/{seed.consecutivo_ot}/historial",
            headers=auth_headers(TALLER_A),
        )
        assert resp.status_code == 200
        eventos = resp.json()
        assert any(
            e["tabla"] == "ordenes_trabajo" and e["evento"] == "Editado" and e["usuario"] == seed.documento_usuario
            for e in eventos
        )

    def test_historial_solo_accesible_para_admin(self, client, orden_pendiente, mecanico_headers):
        resp = client.get(
            f"/api/ordenes-trabajo/{orden_pendiente.consecutivo_ot}/historial",
            headers=mecanico_headers,
        )
        assert resp.status_code == 403


class TestCierraLasViasParalelasAAnulada:
    def test_put_orden_no_permite_fijar_estado_anulada_directamente(self, client, orden_pendiente):
        resp = client.put(
            f"/api/ordenes-trabajo/{orden_pendiente.consecutivo_ot}",
            json={"codOtEstOt": 5},
            headers=auth_headers(TALLER_A),
        )
        assert resp.status_code == 422

    def test_tablero_no_permite_cambiar_estado_a_anulada(self, client, orden_pendiente):
        resp = client.put(
            f"/api/tablero/{orden_pendiente.consecutivo_ot}/estado",
            json={"codEstado": 5},
            headers=auth_headers(TALLER_A),
        )
        assert resp.status_code == 400
