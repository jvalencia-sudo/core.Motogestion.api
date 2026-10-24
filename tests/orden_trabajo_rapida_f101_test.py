"""F1-01: abrir una orden de trabajo solo con placa, kilometraje y motivo del
cliente -- sin mecánico ni productos. Cubre los 3 criterios de aceptación:
(1) creación corta sin mecánico/productos, (2) la orden sigue siendo visible
en listado/tablero (antes desaparecía: 3 vistas unían el mecánico con
INNER JOIN), (3) el API rechaza pasar a Completada/Entregada sin ítems."""
import pytest

from tests.conftest import TALLER_A, auth_headers

# mock_auth0 no es autouse (ver conftest.py): todo este archivo hace requests
# HTTP autenticados con auth_headers(), así que lo necesita entero.
pytestmark = [pytest.mark.db, pytest.mark.usefixtures("mock_auth0")]


@pytest.fixture
def limpiar_ordenes_creadas(db_conn):
    """Las órdenes que crea cada test quedan en la BD (consecutivo_ot no se
    recicla) -- se borran al terminar para no filtrar estado a otros tests
    del módulo (seed_talleres es scope=module)."""
    creadas = []
    yield creadas
    if not creadas:
        return
    with db_conn.cursor() as cur:
        cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(TALLER_A),))
        for consecutivo in creadas:
            cur.execute(
                "DELETE FROM detalle_orden_trabajo WHERE cod_taller = %s AND consecutivo_ot_deto = %s",
                (TALLER_A, consecutivo),
            )
            cur.execute(
                "DELETE FROM orden_estado_historial WHERE cod_taller = %s AND consecutivo_ot = %s",
                (TALLER_A, consecutivo),
            )
            cur.execute(
                "DELETE FROM ordenes_trabajo WHERE cod_taller = %s AND consecutivo_ot = %s",
                (TALLER_A, consecutivo),
            )


def _crear_orden_rapida(client, seed, headers, **overrides):
    payload = {
        "placa_mot_ot": seed.placa_moto,
        "kilometraje_ingreso_ot": 12345,
        "observacion_cli_ot": "Se apaga en frío",
    }
    payload.update(overrides)
    return client.post("/api/ordenes-trabajo", json=payload, headers=headers)


class TestOrdenRapidaSinMecanicoNiProductos:
    def test_se_puede_crear_sin_mecanico_ni_productos(
        self, client, seed_talleres, limpiar_ordenes_creadas
    ):
        seed = seed_talleres[TALLER_A]
        resp = _crear_orden_rapida(client, seed, auth_headers(TALLER_A))
        assert resp.status_code == 201
        data = resp.json()
        limpiar_ordenes_creadas.append(data["consecutivoOt"])

        assert data["documentoMecanico"] is None
        assert data["mecanico"] is None
        assert data["codOtEstOt"] == 1  # Pendiente
        assert data["detalles"] == []

    def test_recepcionista_por_defecto_es_el_usuario_autenticado(
        self, client, seed_talleres, limpiar_ordenes_creadas
    ):
        seed = seed_talleres[TALLER_A]
        resp = _crear_orden_rapida(client, seed, auth_headers(TALLER_A))
        assert resp.status_code == 201
        data = resp.json()
        limpiar_ordenes_creadas.append(data["consecutivoOt"])

        assert data["documentoRecepcionista"] == seed.documento_usuario

    def test_orden_sin_mecanico_aparece_en_listado_y_tablero(
        self, client, seed_talleres, limpiar_ordenes_creadas
    ):
        """Regresión: vw_ordenes_trabajo_completa y vw_ot_pendientes unían al
        mecánico con INNER JOIN -- una orden sin mecánico quedaba invisible en
        el listado y en el tablero Kanban (no un bug de Python, de la vista)."""
        seed = seed_talleres[TALLER_A]
        resp = _crear_orden_rapida(client, seed, auth_headers(TALLER_A))
        assert resp.status_code == 201
        consecutivo = resp.json()["consecutivoOt"]
        limpiar_ordenes_creadas.append(consecutivo)

        listado = client.get("/api/ordenes-trabajo", headers=auth_headers(TALLER_A))
        assert listado.status_code == 200
        assert any(o["consecutivoOt"] == consecutivo for o in listado.json())

        detalle = client.get(f"/api/ordenes-trabajo/{consecutivo}", headers=auth_headers(TALLER_A))
        assert detalle.status_code == 200

        tablero = client.get("/api/tablero", headers=auth_headers(TALLER_A))
        assert tablero.status_code == 200
        assert any(o["consecutivoOt"] == consecutivo for o in tablero.json()["items"])


class TestNoCompletarNiEntregarSinItems:
    def test_no_puede_cambiar_a_completada_sin_items(
        self, client, seed_talleres, limpiar_ordenes_creadas
    ):
        seed = seed_talleres[TALLER_A]
        creada = _crear_orden_rapida(client, seed, auth_headers(TALLER_A))
        consecutivo = creada.json()["consecutivoOt"]
        limpiar_ordenes_creadas.append(consecutivo)

        resp = client.patch(
            f"/api/ordenes-trabajo/{consecutivo}/estado",
            json={"cod_ot_est_ot": 3},
            headers=auth_headers(TALLER_A),
        )
        assert resp.status_code == 400

    def test_no_puede_cambiar_a_entregada_sin_items(
        self, client, seed_talleres, limpiar_ordenes_creadas
    ):
        seed = seed_talleres[TALLER_A]
        creada = _crear_orden_rapida(client, seed, auth_headers(TALLER_A))
        consecutivo = creada.json()["consecutivoOt"]
        limpiar_ordenes_creadas.append(consecutivo)

        resp = client.patch(
            f"/api/ordenes-trabajo/{consecutivo}/estado",
            json={"cod_ot_est_ot": 4},
            headers=auth_headers(TALLER_A),
        )
        assert resp.status_code == 400

    def test_no_se_puede_crear_directo_en_completada_sin_items(
        self, client, seed_talleres, limpiar_ordenes_creadas
    ):
        seed = seed_talleres[TALLER_A]
        resp = _crear_orden_rapida(client, seed, auth_headers(TALLER_A), cod_ot_est_ot=3)
        assert resp.status_code == 400
        # No se creó nada que limpiar (falló antes del INSERT).

    def test_si_puede_cambiar_a_completada_con_items(
        self, client, seed_talleres, limpiar_ordenes_creadas
    ):
        """Control: el bloqueo es por falta de ítems, no un bloqueo general del
        estado Completada."""
        seed = seed_talleres[TALLER_A]
        creada = _crear_orden_rapida(client, seed, auth_headers(TALLER_A))
        consecutivo = creada.json()["consecutivoOt"]
        limpiar_ordenes_creadas.append(consecutivo)

        agregar = client.post(
            f"/api/ordenes-trabajo/{consecutivo}/productos",
            json={"cod_pro_deto": seed.cod_producto, "cantidad_deto": 1},
            headers=auth_headers(TALLER_A),
        )
        assert agregar.status_code == 200

        resp = client.patch(
            f"/api/ordenes-trabajo/{consecutivo}/estado",
            json={"cod_ot_est_ot": 3},
            headers=auth_headers(TALLER_A),
        )
        assert resp.status_code == 200
        assert resp.json()["codOtEstOt"] == 3
