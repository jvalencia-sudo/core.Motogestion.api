"""F1-09: personalización visual de la orden (logo, color, condiciones, pie,
interruptores) + vista previa sin guardar.

Cubre los criterios de aceptación verificables sin un navegador real (el
logo/color/textos realmente impresos en la carta y la tirilla se verificaron
manualmente, ver PR): texto con <, & o <img ...> aparece literal (F0-10), un
SVG o un archivo de 10MB son rechazados, y la vista previa no persiste nada.
"""
import io
from unittest.mock import patch

import pytest
from PIL import Image

from domain.models.auth.user_model import UserPermissionsModel
from tests.conftest import TALLER_A, _SUB_POR_TOKEN, auth_headers

pytestmark = [pytest.mark.db, pytest.mark.usefixtures("mock_auth0")]

NO_ADMIN_TOKEN = "test-token-taller-a-no-admin-f109"
NO_ADMIN_SUB = "test|taller-a-no-admin-f109"
NO_ADMIN_DOCUMENTO = "900100599"


def _png_bytes(width=100, height=100, color="red") -> bytes:
    img = Image.new("RGB", (width, height), color=color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def config_limpia(db_conn):
    """Deja la personalización del taller en su estado por defecto antes y
    después de cada test."""

    def _limpiar():
        with db_conn.cursor() as cur:
            cur.execute(
                "UPDATE talleres SET nombre_comercial_tal = NULL, whatsapp_tal = NULL, "
                "  color_principal_tal = '#00B06E', texto_condiciones_tal = NULL, "
                "  texto_pie_tal = NULL, mostrar_precios_unitarios_tal = true, "
                "  mostrar_mecanico_tal = true, mostrar_firma_cliente_tal = false "
                "WHERE cod_taller = %s",
                (TALLER_A,),
            )
            cur.execute("DELETE FROM taller_logo WHERE cod_taller = %s", (TALLER_A,))

    _limpiar()
    yield
    _limpiar()


def _payload_base(**overrides):
    payload = {
        "modoManoObra": "HORAS",
        "tarifaHoraPred": 10000,
        "nombreComercialTal": "Taller Pro Motos",
        "whatsappTal": "3000000000",
        "colorPrincipalTal": "#1A2B3C",
        "textoCondicionesTal": "Garantía 30 días en mano de obra.",
        "textoPieTal": "Gracias por su visita",
        "mostrarPreciosUnitariosTal": False,
        "mostrarMecanicoTal": False,
        "mostrarFirmaClienteTal": True,
    }
    payload.update(overrides)
    return payload


class TestConfigPersonalizacion:
    def test_guardar_y_leer_personalizacion(self, client, seed_talleres, config_limpia):
        resp = client.put("/api/talleres/config", json=_payload_base(), headers=auth_headers(TALLER_A))
        assert resp.status_code == 200
        data = resp.json()
        assert data["nombreComercialTal"] == "Taller Pro Motos"
        assert data["colorPrincipalTal"] == "#1A2B3C"
        assert data["mostrarPreciosUnitariosTal"] is False
        assert data["tieneLogo"] is False

        resp2 = client.get("/api/talleres/config", headers=auth_headers(TALLER_A))
        assert resp2.status_code == 200
        assert resp2.json()["textoCondicionesTal"] == "Garantía 30 días en mano de obra."

    def test_color_invalido_es_422(self, client, seed_talleres, config_limpia):
        resp = client.put(
            "/api/talleres/config",
            json=_payload_base(colorPrincipalTal="no-es-un-color"),
            headers=auth_headers(TALLER_A),
        )
        assert resp.status_code == 422

    def test_condiciones_muy_largas_son_422(self, client, seed_talleres, config_limpia):
        resp = client.put(
            "/api/talleres/config",
            json=_payload_base(textoCondicionesTal="x" * 1501),
            headers=auth_headers(TALLER_A),
        )
        assert resp.status_code == 422


class TestLogo:
    def test_subir_logo_valido_y_servirlo(self, client, seed_talleres, config_limpia):
        resp = client.post(
            "/api/talleres/logo",
            files={"file": ("logo.png", _png_bytes(), "image/png")},
            headers=auth_headers(TALLER_A),
        )
        assert resp.status_code == 200

        config = client.get("/api/talleres/config", headers=auth_headers(TALLER_A)).json()
        assert config["tieneLogo"] is True

        logo_resp = client.get("/api/talleres/logo", headers=auth_headers(TALLER_A))
        assert logo_resp.status_code == 200
        assert logo_resp.headers["content-type"] == "image/png"
        assert len(logo_resp.content) > 0

    def test_reemplazar_logo_actualiza_el_servido(self, client, seed_talleres, config_limpia):
        client.post(
            "/api/talleres/logo",
            files={"file": ("logo.png", _png_bytes(color="red"), "image/png")},
            headers=auth_headers(TALLER_A),
        )
        primero = client.get("/api/talleres/logo", headers=auth_headers(TALLER_A)).content

        client.post(
            "/api/talleres/logo",
            files={"file": ("logo.png", _png_bytes(color="blue"), "image/png")},
            headers=auth_headers(TALLER_A),
        )
        segundo = client.get("/api/talleres/logo", headers=auth_headers(TALLER_A)).content

        assert primero != segundo

    def test_logo_svg_es_rechazado(self, client, seed_talleres, config_limpia):
        svg = b'<svg xmlns="http://www.w3.org/2000/svg"></svg>'
        resp = client.post(
            "/api/talleres/logo",
            files={"file": ("logo.svg", svg, "image/svg+xml")},
            headers=auth_headers(TALLER_A),
        )
        assert resp.status_code == 400

    def test_logo_mayor_a_2mb_es_rechazado(self, client, seed_talleres, config_limpia):
        contenido = b"\x00" * (2 * 1024 * 1024 + 1)
        resp = client.post(
            "/api/talleres/logo",
            files={"file": ("logo.png", contenido, "image/png")},
            headers=auth_headers(TALLER_A),
        )
        assert resp.status_code == 400

    def test_archivo_de_10mb_es_rechazado(self, client, seed_talleres, config_limpia):
        contenido = b"\x00" * (10 * 1024 * 1024)
        resp = client.post(
            "/api/talleres/logo",
            files={"file": ("logo.png", contenido, "image/png")},
            headers=auth_headers(TALLER_A),
        )
        assert resp.status_code == 400

    def test_logo_disfrazado_de_png_pero_no_es_imagen_es_rechazado(self, client, seed_talleres, config_limpia):
        """content-type correcto pero bytes basura: Pillow no puede decodificarlo --
        defensa en profundidad si el content-type viene mal etiquetado."""
        resp = client.post(
            "/api/talleres/logo",
            files={"file": ("logo.png", b"esto no es un PNG real", "image/png")},
            headers=auth_headers(TALLER_A),
        )
        assert resp.status_code == 400

    def test_sin_logo_es_404(self, client, seed_talleres, config_limpia):
        resp = client.get("/api/talleres/logo", headers=auth_headers(TALLER_A))
        assert resp.status_code == 404


class TestVistaPrevia:
    def test_vista_previa_devuelve_pdf_sin_guardar(self, client, seed_talleres, config_limpia):
        payload = {
            "nombreComercialTal": "Vista previa taller",
            "colorPrincipalTal": "#FF00FF",
            "textoCondicionesTal": "Condiciones de prueba <script>evil()</script> & <img src=x>",
            "textoPieTal": "Pie de prueba",
            "mostrarPreciosUnitariosTal": False,
            "mostrarMecanicoTal": False,
            "mostrarFirmaClienteTal": True,
        }
        resp = client.post("/api/talleres/vista-previa-pdf", json=payload, headers=auth_headers(TALLER_A))
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"
        assert resp.content[:4] == b"%PDF"

        # No debe haber guardado nada en talleres: la config sigue en default.
        config = client.get("/api/talleres/config", headers=auth_headers(TALLER_A)).json()
        assert config["nombreComercialTal"] is None
        assert config["colorPrincipalTal"] == "#00B06E"

    def test_vista_previa_valores_por_defecto(self, client, seed_talleres, config_limpia):
        resp = client.post("/api/talleres/vista-previa-pdf", json={}, headers=auth_headers(TALLER_A))
        assert resp.status_code == 200
        assert resp.content[:4] == b"%PDF"


@pytest.fixture
def no_admin_headers(db_conn, seed_talleres):
    """Usuario real en TALLER_A sin es_admin_usu (require_admin debe rechazarlo
    aunque el token mockeado traiga permissions=['*'] -- require_admin lee
    es_admin_usu de la BD, no la lista de permisos del token)."""
    cod_taller = TALLER_A
    with db_conn.cursor() as cur:
        cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(cod_taller),))
        cur.execute(
            "INSERT INTO perfiles (cod_taller, es_admin, cod_est_prf, nombre_prf) "
            "VALUES (%s, false, 1, 'No admin F1-09 test') RETURNING cod_prf",
            (cod_taller,),
        )
        cod_prf = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO usuarios (cod_taller, documento_usu, nombre_usu, apellido_1_usu, "
            "correo_usu, contrasena_usu, cod_tipo_usu, cod_est_usu, sub_id_usu, "
            "cod_prf_usu, es_admin_usu) "
            "VALUES (%s, %s, 'No', 'Admin', %s, 'test', 1, 1, %s, %s, false)",
            (cod_taller, NO_ADMIN_DOCUMENTO, "no-admin-f109@test.local", NO_ADMIN_SUB, cod_prf),
        )

    async def _verify(self, token: str) -> UserPermissionsModel:
        if token == NO_ADMIN_TOKEN:
            return UserPermissionsModel(user_id=NO_ADMIN_SUB, permissions=["*"])
        sub = _SUB_POR_TOKEN.get(token)
        if sub is None:
            raise ValueError(f"Token de test desconocido: {token!r}")
        return UserPermissionsModel(user_id=sub, permissions=["*"])

    with patch(
        "infrastructure.providers.auth.auth0_provider.Auth0Provider.verify",
        new=_verify,
    ):
        yield {"Authorization": f"Bearer {NO_ADMIN_TOKEN}"}

    with db_conn.cursor() as cur:
        cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(cod_taller),))
        cur.execute("DELETE FROM usuarios WHERE documento_usu = %s", (NO_ADMIN_DOCUMENTO,))
        cur.execute("DELETE FROM perfiles WHERE cod_taller = %s AND cod_prf = %s", (cod_taller, cod_prf))


class TestPermisos:
    def test_subir_logo_sin_admin_es_403(self, client, seed_talleres, no_admin_headers):
        resp = client.post(
            "/api/talleres/logo",
            files={"file": ("logo.png", _png_bytes(), "image/png")},
            headers=no_admin_headers,
        )
        assert resp.status_code == 403

    def test_vista_previa_sin_admin_es_403(self, client, seed_talleres, no_admin_headers):
        resp = client.post("/api/talleres/vista-previa-pdf", json={}, headers=no_admin_headers)
        assert resp.status_code == 403

    def test_obtener_logo_sin_admin_es_403(self, client, seed_talleres, no_admin_headers):
        resp = client.get("/api/talleres/logo", headers=no_admin_headers)
        assert resp.status_code == 403
