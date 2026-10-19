"""F1-02: búsqueda por placa como pantalla principal. Cubre los 2 criterios de
aceptación que tocan al backend: (1) 'abc 12d', 'ABC-12D' y 'ABC12D' encuentran
la misma moto, tanto al guardar como al buscar; (2) el historial de una moto
(usado por el buscador de /inicio) trae fecha, kilometraje y trabajos."""
import pytest

from tests.conftest import TALLER_A, auth_headers

pytestmark = [pytest.mark.db, pytest.mark.usefixtures("mock_auth0")]


class TestNormalizacionPlacaAlBuscar:
    def test_busca_moto_con_distintos_formatos_de_la_misma_placa(
        self, client, seed_talleres
    ):
        seed = seed_talleres[TALLER_A]
        placa = seed.placa_moto  # ej. "T001AA" -- exactamente 6 chars, sin espacios/guiones
        headers = auth_headers(TALLER_A)

        variantes = [
            placa,
            placa.lower(),
            f"{placa[0]} {placa[1:4]}-{placa[4:]}".lower(),
        ]
        for variante in variantes:
            resp = client.get(f"/api/motos/{variante}", headers=headers)
            assert resp.status_code == 200, variante
            assert resp.json()["placaMot"] == placa

    def test_busca_ordenes_de_moto_con_distintos_formatos_de_la_misma_placa(
        self, client, seed_talleres
    ):
        seed = seed_talleres[TALLER_A]
        placa = seed.placa_moto
        headers = auth_headers(TALLER_A)

        variante = f"{placa[0]} {placa[1:4]}-{placa[4:]}".lower()
        resp = client.get(f"/api/ordenes-trabajo/moto/{variante}", headers=headers)
        assert resp.status_code == 200
        ordenes = resp.json()
        assert any(o["consecutivoOt"] == seed.consecutivo_ot for o in ordenes)

    def test_crear_moto_normaliza_la_placa_antes_de_guardar(
        self, client, seed_talleres, db_conn
    ):
        seed = seed_talleres[TALLER_A]
        headers = auth_headers(TALLER_A)
        placa_sucia = "zm 99-x"  # -> "ZM99X" tras normalizar (5 chars, válida)

        resp = client.post(
            "/api/motos",
            headers=headers,
            json={
                "placaMot": placa_sucia,
                "modeloMot": 2022,
                "colorMot": "Negro",
                "cilindrajeMot": 150,
                "documentoCliMot": seed.documento_cliente,
                "codMarcaMot": seed.cod_marca,
            },
        )
        try:
            assert resp.status_code == 201
            assert resp.json()["placaMot"] == "ZM99X"

            # La fila en BD tiene que estar guardada ya normalizada, no cruda.
            with db_conn.cursor() as cur:
                cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(TALLER_A),))
                cur.execute(
                    "SELECT placa_mot FROM motos WHERE cod_taller = %s AND placa_mot = 'ZM99X'",
                    (TALLER_A,),
                )
                assert cur.fetchone() is not None
        finally:
            with db_conn.cursor() as cur:
                cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(TALLER_A),))
                cur.execute(
                    "DELETE FROM motos WHERE cod_taller = %s AND placa_mot = 'ZM99X'",
                    (TALLER_A,),
                )


class TestPlacasDeCincoCaracteres:
    """Regresión: obtener_moto_por_id exigía len(placa) == 6 exacto, pero
    MotoCreateContract ya permitía 5-6 (hay placas de moto colombianas de 5
    caracteres, ej. 'CQZ69') -- una moto con placa de 5 se podía crear pero
    nunca se podía volver a encontrar."""

    def test_se_puede_crear_y_luego_buscar_una_moto_con_placa_de_5_caracteres(
        self, client, seed_talleres, db_conn
    ):
        seed = seed_talleres[TALLER_A]
        headers = auth_headers(TALLER_A)
        placa = "CQZ69"

        resp = client.post(
            "/api/motos",
            headers=headers,
            json={
                "placaMot": placa,
                "modeloMot": 2021,
                "colorMot": "Rojo",
                "cilindrajeMot": 125,
                "documentoCliMot": seed.documento_cliente,
                "codMarcaMot": seed.cod_marca,
            },
        )
        try:
            assert resp.status_code == 201

            busqueda = client.get(f"/api/motos/{placa}", headers=headers)
            assert busqueda.status_code == 200
            assert busqueda.json()["placaMot"] == placa
        finally:
            with db_conn.cursor() as cur:
                cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(TALLER_A),))
                cur.execute(
                    "DELETE FROM motos WHERE cod_taller = %s AND placa_mot = %s",
                    (TALLER_A, placa),
                )


class TestHistorialPorMoto:
    def test_historial_trae_kilometraje_estado_y_trabajos(
        self, client, seed_talleres
    ):
        """El seed de taller crea una orden (consecutivo_ot) con km=15000, estado
        Pendiente (cod 1) y un detalle de 'Producto de prueba' -- el buscador de
        placa necesita esos 3 datos para armar el historial sin llamadas extra."""
        seed = seed_talleres[TALLER_A]
        headers = auth_headers(TALLER_A)

        resp = client.get(f"/api/ordenes-trabajo/moto/{seed.placa_moto}", headers=headers)
        assert resp.status_code == 200
        orden = next(o for o in resp.json() if o["consecutivoOt"] == seed.consecutivo_ot)

        assert orden["kilometrajeIngresoOt"] == 15000
        assert orden["codOtEstOt"] == 1
        assert orden["trabajos"] == "Producto de prueba"
