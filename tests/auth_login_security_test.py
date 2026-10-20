"""BLOQUEANTE 1 (seguridad, antes del piloto): toma de cuentas en
POST /api/auth/login. El correo del body de la petición NUNCA decide a qué
cuenta se vincula un sub de Auth0 nuevo -- solo el correo VERIFICADO del
propio perfil de Auth0 (Management API) puede hacerlo, y nunca se revincula
un correo que ya tiene un sub_id_usu de OTRA cuenta."""
from unittest.mock import AsyncMock, patch

import pytest

from domain.models.auth.user_model import UserPermissionsModel
from tests.conftest import TALLER_A, _SUB_POR_TALLER, _SUB_POR_TOKEN

pytestmark = [pytest.mark.db, pytest.mark.usefixtures("mock_auth0")]

ATACANTE_SUB = "test|atacante-f0-seguridad"
ATACANTE_TOKEN = "test-token-atacante-f0-seguridad"


async def _verify_con_atacante(self, token: str):
    if token == ATACANTE_TOKEN:
        return UserPermissionsModel(user_id=ATACANTE_SUB, permissions=["*"])
    sub = _SUB_POR_TOKEN.get(token)
    if sub is None:
        raise ValueError(f"Token de test desconocido: {token!r}")
    return UserPermissionsModel(user_id=sub, permissions=["*"])


def test_no_se_puede_tomar_otra_cuenta_mandando_su_correo_en_el_body(client, db_conn, seed_talleres):
    """El atacante tiene su PROPIO token válido (su sub real, verificado por
    Auth0) pero manda el correo de la VÍCTIMA en el body. Si el fix funciona,
    el correo del body se ignora por completo: se usa el correo verificado
    REAL del atacante ("atacante@evil.com", que no está pre-registrado), así
    que el login falla -- y la fila de la víctima no se toca."""
    seed = seed_talleres[TALLER_A]
    correo_victima = f"user{TALLER_A}@test.local"
    with patch(
        "infrastructure.providers.auth.auth0_provider.Auth0Provider.verify",
        new=_verify_con_atacante,
    ), patch(
        "infrastructure.providers.auth.auth0_provider.Auth0Provider.get_user_info",
        new=AsyncMock(return_value={"email": "atacante@evil.com", "email_verified": True}),
    ):
        resp = client.post(
            "/api/auth/login",
            json={"email": correo_victima, "token": ATACANTE_TOKEN, "name": "Atacante"},
        )
    assert resp.status_code == 403
    assert "no registrado" in resp.json()["message"].lower()

    with db_conn.cursor() as cur:
        cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(TALLER_A),))
        cur.execute(
            "SELECT sub_id_usu FROM usuarios WHERE documento_usu = %s", (seed.documento_usuario,)
        )
        assert cur.fetchone()[0] == _SUB_POR_TALLER[TALLER_A]


def test_correo_sin_verificar_rechaza(client):
    with patch(
        "infrastructure.providers.auth.auth0_provider.Auth0Provider.verify",
        new=_verify_con_atacante,
    ), patch(
        "infrastructure.providers.auth.auth0_provider.Auth0Provider.get_user_info",
        new=AsyncMock(return_value={"email": "alguien@example.com", "email_verified": False}),
    ):
        resp = client.post(
            "/api/auth/login",
            json={"email": "alguien@example.com", "token": ATACANTE_TOKEN, "name": "Alguien"},
        )
    assert resp.status_code == 403
    assert "verificado" in resp.json()["message"].lower()


def test_management_api_caida_no_dice_correo_sin_verificar(client):
    """Revisión: cuando get_user_info() no pudo hablar con Auth0 (devuelve
    None), el mensaje antes decía "correo no verificado" -- falso, Auth0 ni
    siquiera respondió. Debe decir explícitamente que no se pudo verificar la
    cuenta, no inventar un motivo."""
    with patch(
        "infrastructure.providers.auth.auth0_provider.Auth0Provider.verify",
        new=_verify_con_atacante,
    ), patch(
        "infrastructure.providers.auth.auth0_provider.Auth0Provider.get_user_info",
        new=AsyncMock(return_value=None),
    ):
        resp = client.post(
            "/api/auth/login",
            json={"email": "alguien@example.com", "token": ATACANTE_TOKEN, "name": "Alguien"},
        )
    assert resp.status_code == 403
    mensaje = resp.json()["message"].lower()
    assert "no pudimos verificar" in mensaje
    assert "no verificado" not in mensaje


def test_email_verified_como_texto_no_cuela_como_verificado(client):
    """Antes el chequeo era `not info.get("email_verified")` -- con el string
    "false" (verdadero para Python, `not "false"` es False) el login seguiría
    de largo creyendo que el correo SÍ está verificado. Debe exigir
    exactamente `True`, no cualquier valor truthy."""
    with patch(
        "infrastructure.providers.auth.auth0_provider.Auth0Provider.verify",
        new=_verify_con_atacante,
    ), patch(
        "infrastructure.providers.auth.auth0_provider.Auth0Provider.get_user_info",
        new=AsyncMock(return_value={"email": "alguien@example.com", "email_verified": "false"}),
    ):
        resp = client.post(
            "/api/auth/login",
            json={"email": "alguien@example.com", "token": ATACANTE_TOKEN, "name": "Alguien"},
        )
    assert resp.status_code == 403
    assert "verificado" in resp.json()["message"].lower()


def test_correo_ya_vinculado_a_otra_cuenta_rechaza(client):
    """El correo del taller A ya tiene sub_id_usu = test|taller-a. Si otro sub
    (distinto) se presenta con ESE mismo correo como verificado, se rechaza --
    no se revincula ni se deja pasar."""
    with patch(
        "infrastructure.providers.auth.auth0_provider.Auth0Provider.verify",
        new=_verify_con_atacante,
    ), patch(
        "infrastructure.providers.auth.auth0_provider.Auth0Provider.get_user_info",
        new=AsyncMock(
            return_value={"email": f"user{TALLER_A}@test.local", "email_verified": True}
        ),
    ):
        resp = client.post(
            "/api/auth/login",
            json={
                "email": f"user{TALLER_A}@test.local",
                "token": ATACANTE_TOKEN,
                "name": "Atacante",
            },
        )
    assert resp.status_code == 403
    assert "vinculado" in resp.json()["message"].lower()


def test_primer_ingreso_legitimo_vincula_correctamente(client, db_conn, seed_talleres):
    """Un usuario PRE-REGISTRADO (sub_id_usu IS NULL, como lo deja una
    invitación real) sí puede entrar la primera vez: su correo verificado
    coincide con el pre-registrado, y no tiene sub previo de nadie más."""
    cod_taller = TALLER_A
    documento = "900111222"
    correo = "pre-registrado-f0-seguridad@test.local"
    with db_conn.cursor() as cur:
        cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(cod_taller),))
        cur.execute(
            "INSERT INTO usuarios (cod_taller, documento_usu, nombre_usu, apellido_1_usu, "
            "correo_usu, contrasena_usu, cod_tipo_usu, cod_est_usu, sub_id_usu, "
            "cod_prf_usu, es_admin_usu) "
            "VALUES (%s, %s, 'Pre', 'Registrado', %s, 'auth0_managed', 1, 1, NULL, "
            "(SELECT cod_prf FROM perfiles WHERE cod_taller=%s AND es_admin=true LIMIT 1), true)",
            (cod_taller, documento, correo, cod_taller),
        )
    try:
        with patch(
            "infrastructure.providers.auth.auth0_provider.Auth0Provider.verify",
            new=_verify_con_atacante,
        ), patch(
            "infrastructure.providers.auth.auth0_provider.Auth0Provider.get_user_info",
            new=AsyncMock(return_value={"email": correo, "email_verified": True}),
        ):
            resp = client.post(
                "/api/auth/login",
                json={"email": correo, "token": ATACANTE_TOKEN, "name": "Nuevo"},
            )
        assert resp.status_code == 200, resp.text

        with db_conn.cursor() as cur:
            cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(cod_taller),))
            cur.execute("SELECT sub_id_usu FROM usuarios WHERE documento_usu = %s", (documento,))
            assert cur.fetchone()[0] == ATACANTE_SUB
    finally:
        with db_conn.cursor() as cur:
            cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(cod_taller),))
            cur.execute("DELETE FROM usuarios WHERE documento_usu = %s", (documento,))
