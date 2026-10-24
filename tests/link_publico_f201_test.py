"""F2-01: link público de estado de una orden (sin login). Token UUID
impredecible (no el consecutivo), nunca expone documento/correo/dirección
del cliente, respeta el toggle de "mostrar ítems y total" del taller, y se
puede regenerar (invalida el anterior de inmediato)."""
import pytest

from tests.conftest import TALLER_A, TALLER_B, auth_headers

pytestmark = [pytest.mark.db, pytest.mark.usefixtures("mock_auth0")]


def _token_de(client, cod_taller: int, consecutivo_ot: int) -> str:
    resp = client.get(
        f"/api/ordenes-trabajo/{consecutivo_ot}",
        headers=auth_headers(cod_taller),
    )
    assert resp.status_code == 200
    return resp.json()["tokenPublico"]


class TestTokenInvalidoDa404:
    def test_token_que_no_existe_da_404(self, client):
        resp = client.get(
            "/api/public/ordenes-trabajo/estado/00000000-0000-0000-0000-000000000000"
        )
        assert resp.status_code == 404

    def test_token_mal_formado_da_404(self, client):
        resp = client.get("/api/public/ordenes-trabajo/estado/no-es-un-uuid")
        assert resp.status_code == 404

    def test_cambiar_un_caracter_del_token_da_404(self, client, seed_talleres):
        seed = seed_talleres[TALLER_A]
        token = _token_de(client, TALLER_A, seed.consecutivo_ot)
        primer_caracter = token[0]
        reemplazo = "a" if primer_caracter != "a" else "b"
        token_alterado = reemplazo + token[1:]

        resp = client.get(f"/api/public/ordenes-trabajo/estado/{token_alterado}")
        assert resp.status_code == 404


class TestTokenValidoNoFiltraDatosSensibles:
    def test_token_valido_da_200_con_los_datos_de_la_moto(self, client, seed_talleres):
        seed = seed_talleres[TALLER_A]
        token = _token_de(client, TALLER_A, seed.consecutivo_ot)

        resp = client.get(f"/api/public/ordenes-trabajo/estado/{token}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["placaMot"] == seed.placa_moto
        assert data["codOtEstOt"] == 1
        assert data["consecutivoOt"] == seed.consecutivo_ot
        assert data["kilometrajeIngresoOt"] == 15000
        # F2-01 fase 2: cada ítem trae su tipo para agrupar repuestos/mano de obra.
        assert data["items"][0]["tipo"] == "BIEN"

    def test_no_incluye_documento_correo_ni_direccion_del_cliente(self, client, seed_talleres):
        seed = seed_talleres[TALLER_A]
        token = _token_de(client, TALLER_A, seed.consecutivo_ot)

        resp = client.get(f"/api/public/ordenes-trabajo/estado/{token}")
        assert resp.status_code == 200
        data = resp.json()
        assert "documentoCli" not in data
        assert "correoCli" not in data
        assert "direccionCli" not in data
        assert "nombreCompletoCliente" not in data
        # tampoco como substring en algún valor anidado (ej. del taller).
        assert seed.documento_cliente not in resp.text


class TestToggleDeDetallePublico:
    def test_mostrar_detalle_publico_false_oculta_items_y_total(self, client, db_conn, seed_talleres):
        seed = seed_talleres[TALLER_A]
        token = _token_de(client, TALLER_A, seed.consecutivo_ot)

        with db_conn.cursor() as cur:
            cur.execute(
                "UPDATE talleres SET mostrar_detalle_publico_tal = false WHERE cod_taller = %s",
                (TALLER_A,),
            )
        try:
            resp = client.get(f"/api/public/ordenes-trabajo/estado/{token}")
            assert resp.status_code == 200
            data = resp.json()
            assert data["items"] is None
            assert data["totalOt"] is None
        finally:
            with db_conn.cursor() as cur:
                cur.execute(
                    "UPDATE talleres SET mostrar_detalle_publico_tal = true WHERE cod_taller = %s",
                    (TALLER_A,),
                )

    def test_por_defecto_muestra_items(self, client, seed_talleres):
        seed = seed_talleres[TALLER_A]
        token = _token_de(client, TALLER_A, seed.consecutivo_ot)

        resp = client.get(f"/api/public/ordenes-trabajo/estado/{token}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] is not None
        assert len(data["items"]) == 1


class TestRegenerarToken:
    def test_regenerar_invalida_el_token_anterior(self, client, seed_talleres):
        seed = seed_talleres[TALLER_A]
        token_viejo = _token_de(client, TALLER_A, seed.consecutivo_ot)

        regenerar = client.patch(
            f"/api/ordenes-trabajo/{seed.consecutivo_ot}/token-publico/regenerar",
            headers=auth_headers(TALLER_A),
        )
        assert regenerar.status_code == 200
        token_nuevo = regenerar.json()["tokenPublico"]
        assert token_nuevo != token_viejo

        assert client.get(f"/api/public/ordenes-trabajo/estado/{token_viejo}").status_code == 404
        assert client.get(f"/api/public/ordenes-trabajo/estado/{token_nuevo}").status_code == 200

    def test_regenerar_sin_sesion_da_401(self, client, seed_talleres):
        seed = seed_talleres[TALLER_A]
        resp = client.patch(f"/api/ordenes-trabajo/{seed.consecutivo_ot}/token-publico/regenerar")
        assert resp.status_code == 401

    def test_no_se_puede_regenerar_el_token_de_otro_taller(self, client, seed_talleres):
        seed_b = seed_talleres[TALLER_B]
        resp = client.patch(
            f"/api/ordenes-trabajo/{seed_b.consecutivo_ot}/token-publico/regenerar",
            headers=auth_headers(TALLER_A),
        )
        assert resp.status_code == 404


def test_el_token_de_un_taller_nunca_expone_datos_del_otro(client, seed_talleres):
    seed_a = seed_talleres[TALLER_A]
    seed_b = seed_talleres[TALLER_B]
    token_a = _token_de(client, TALLER_A, seed_a.consecutivo_ot)

    resp = client.get(f"/api/public/ordenes-trabajo/estado/{token_a}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["placaMot"] == seed_a.placa_moto
    assert data["placaMot"] != seed_b.placa_moto
