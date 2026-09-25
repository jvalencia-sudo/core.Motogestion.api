"""F0-04, revisión: el middleware logueaba la ruta RESUELTA (con el documento
real del cliente en el path), no la plantilla -- este test confirma el fix
end-to-end contra la app real (mismo mecanismo que ya prueba
aislamiento_multitenant_test.py: mock solo de Auth0Provider.verify, el resto de
la cadena corre de verdad contra la BD de test)."""
import logging

import pytest

from tests.conftest import TALLER_A, auth_headers

pytestmark = [pytest.mark.db, pytest.mark.usefixtures("mock_auth0")]


def test_loguea_la_plantilla_de_ruta_no_el_documento_real(client, caplog):
    with caplog.at_level(logging.INFO, logger="request"):
        client.get("/api/clientes/1122334455", headers=auth_headers(TALLER_A))
        # El status exacto no importa para este test (depende de si el cliente
        # existe o de cómo resuelva la auth) -- lo que se prueba es la ruta
        # logueada, no la respuesta.

    registros = [r for r in caplog.records if r.name == "request"]
    assert registros, "no se logueó ninguna línea de request"
    ruta = registros[-1].ruta
    assert ruta == "/api/clientes/{documento_cli}"
    assert "1122334455" not in ruta
