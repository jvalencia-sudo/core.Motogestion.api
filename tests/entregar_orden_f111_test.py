"""F1-11: kilometraje_salida_ot era DATE (y con error de ortografía) mientras
el contrato y el repositorio ya le mandaban un entero -- entregar una orden
con kilometraje de salida fallaba con un error de tipo en Postgres. Cubre los
2 criterios de aceptación de HTTP: (1) entregar con kilometraje de salida
funciona y queda guardado, (2) un kilometraje de salida menor al de ingreso
es rechazado."""
import psycopg
import pytest

from tests.conftest import TALLER_A, auth_headers

pytestmark = [pytest.mark.db, pytest.mark.usefixtures("mock_auth0")]


@pytest.fixture
def orden_finalizada(db_conn, seed_talleres):
    """La orden sembrada por seed_talleres arranca en estado Pendiente (1);
    entregar_orden exige 'Finalizada' (3). Se deja limpia (sin fecha de
    entrega ni km de salida) antes de cada test, sin importar en qué quedó
    un test anterior del mismo módulo."""
    seed = seed_talleres[TALLER_A]
    with db_conn.cursor() as cur:
        cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(TALLER_A),))
        cur.execute(
            "UPDATE ordenes_trabajo SET cod_ot_est_ot = 3, fecha_entrega_ot = NULL, "
            "kilometraje_salida_ot = NULL WHERE cod_taller = %s AND consecutivo_ot = %s",
            (TALLER_A, seed.consecutivo_ot),
        )
    return seed


class TestEntregarConKilometrajeDeSalida:
    def test_entregar_con_kilometraje_de_salida_funciona_y_queda_guardado(
        self, client, orden_finalizada
    ):
        # El seed usa kilometraje_ingreso_ot = 15000 (ver tests/conftest.py).
        resp = client.patch(
            f"/api/ordenes-trabajo/{orden_finalizada.consecutivo_ot}/entregar",
            json={"kilometrajeSalidaOt": 15500},
            headers=auth_headers(TALLER_A),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["kilometrajeSalidaOt"] == 15500
        assert data["codOtEstOt"] == 4  # Entregada

        # Confirma que quedó guardado de verdad, no solo en la respuesta.
        detalle = client.get(
            f"/api/ordenes-trabajo/{orden_finalizada.consecutivo_ot}",
            headers=auth_headers(TALLER_A),
        )
        assert detalle.status_code == 200
        assert detalle.json()["kilometrajeSalidaOt"] == 15500

    def test_kilometraje_de_salida_menor_al_de_ingreso_es_rechazado(
        self, client, orden_finalizada
    ):
        resp = client.patch(
            f"/api/ordenes-trabajo/{orden_finalizada.consecutivo_ot}/entregar",
            json={"kilometrajeSalidaOt": 100},  # < 15000 (km de ingreso del seed)
            headers=auth_headers(TALLER_A),
        )
        assert resp.status_code == 400

        # La orden no debe haber quedado marcada como entregada por el intento fallido.
        with_headers = client.get(
            f"/api/ordenes-trabajo/{orden_finalizada.consecutivo_ot}",
            headers=auth_headers(TALLER_A),
        )
        assert with_headers.json()["codOtEstOt"] == 3

    def test_entregar_sin_kilometraje_de_salida_sigue_funcionando(
        self, client, orden_finalizada
    ):
        """kilometraje_salida_ot es opcional -- no se puede volver obligatorio
        sin romper órdenes que se entregan sin ese dato."""
        resp = client.patch(
            f"/api/ordenes-trabajo/{orden_finalizada.consecutivo_ot}/entregar",
            json={},
            headers=auth_headers(TALLER_A),
        )
        assert resp.status_code == 200
        assert resp.json()["kilometrajeSalidaOt"] is None

    def test_check_de_bd_rechaza_km_salida_menor_al_de_ingreso(
        self, db_conn, orden_finalizada
    ):
        """Defensa en profundidad: el CHECK de la BD protege incluso si algo
        escribe la fila sin pasar por el servicio."""
        with db_conn.cursor() as cur:
            cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(TALLER_A),))
            with pytest.raises(psycopg.errors.CheckViolation):
                cur.execute(
                    "UPDATE ordenes_trabajo SET kilometraje_salida_ot = 1 "
                    "WHERE cod_taller = %s AND consecutivo_ot = %s",
                    (TALLER_A, orden_finalizada.consecutivo_ot),
                )
