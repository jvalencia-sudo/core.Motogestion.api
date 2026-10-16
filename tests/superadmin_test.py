"""F0-14: panel de super-admin de plataforma. es_super_admin es una marca
explícita e independiente de taller/rol -- antes de este ticket "super-admin"
significaba "Admin del taller plataforma (cod_taller=1)", lo que dejaba a
cualquier Admin de ese taller (usado también para demos) con acceso a toda la
plataforma sin que nadie lo hubiera decidido. Cubre: el viejo significado ya
no basta, MFA obligatorio en el login, aislamiento de métricas por tenant, y
que las acciones sobre un taller exigen motivo y quedan en auditoria_superadmin."""

from unittest.mock import AsyncMock, patch

import pytest

from domain.models.auth.user_model import UserPermissionsModel
from domain.services.superadmin.metricas_servicio import MetricasServicio
from tests.conftest import TALLER_A, TALLER_B, _SUB_POR_TOKEN, auth_headers

pytestmark = [pytest.mark.db, pytest.mark.usefixtures("mock_auth0")]

# El admin demo (documento_usu=1000000001, cod_taller=1) ya queda sembrado con
# es_super_admin=true por full_schema_v2_multitenant.sql -- se reusa en vez de
# crear un usuario nuevo para cada test.
SUPERADMIN_SUB = "sub-1000000001"
SUPERADMIN_TOKEN = "test-token-superadmin-f014"


async def _verify_con_superadmin(self, token: str):
    if token == SUPERADMIN_TOKEN:
        return UserPermissionsModel(user_id=SUPERADMIN_SUB, permissions=["*"])
    sub = _SUB_POR_TOKEN.get(token)
    if sub is None:
        raise ValueError(f"Token de test desconocido: {token!r}")
    return UserPermissionsModel(user_id=sub, permissions=["*"])


@pytest.fixture
def superadmin_headers():
    async def _verify(self, token: str):
        return await _verify_con_superadmin(self, token)

    with patch("infrastructure.providers.auth.auth0_provider.Auth0Provider.verify", new=_verify):
        yield {"Authorization": f"Bearer {SUPERADMIN_TOKEN}"}


class TestEsSuperAdminReemplazaElSignificadoViejo:
    def test_admin_normal_no_entra_a_ningun_endpoint_de_superadmin(self, client, seed_talleres):
        resp = client.get("/api/superadmin/resumen", headers=auth_headers(TALLER_A))
        assert resp.status_code == 403

    def test_admin_del_taller_plataforma_sin_la_marca_ya_no_entra(self, client, db_conn):
        """El viejo significado (Admin de cod_taller=1) por sí solo ya NO basta:
        hace falta la marca es_super_admin=true explícita."""
        with db_conn.cursor() as cur:
            cur.execute("SELECT set_config('app.tenant_id', '1', false)")
            cur.execute(
                "INSERT INTO usuarios (cod_taller, documento_usu, nombre_usu, apellido_1_usu, "
                "correo_usu, contrasena_usu, cod_tipo_usu, cod_est_usu, sub_id_usu, "
                "cod_prf_usu, cod_rol_prf_usu, es_super_admin) "
                "VALUES (1, '999888777', 'Admin', 'Sin Marca', 'admin-sin-marca-f014@example.com', "
                "'test', 1, 1, 'sub-999888777', 1, 1, false)"
            )
        token = "test-token-admin-taller1-sin-marca"

        async def _verify(self, t: str):
            if t == token:
                return UserPermissionsModel(user_id="sub-999888777", permissions=["*"])
            return await _verify_con_superadmin(self, t)

        try:
            with patch("infrastructure.providers.auth.auth0_provider.Auth0Provider.verify", new=_verify):
                resp = client.get(
                    "/api/superadmin/resumen", headers={"Authorization": f"Bearer {token}"}
                )
            assert resp.status_code == 403
        finally:
            with db_conn.cursor() as cur:
                cur.execute("SELECT set_config('app.tenant_id', '1', false)")
                cur.execute("DELETE FROM usuarios WHERE documento_usu = '999888777'")

    def test_super_admin_si_entra(self, client, superadmin_headers):
        resp = client.get("/api/superadmin/resumen", headers=superadmin_headers)
        assert resp.status_code == 200
        assert "mrr" in resp.json()


class TestMFAObligatorioParaSuperAdmin:
    def test_login_sin_mfa_falla(self, client):
        with patch(
            "infrastructure.providers.auth.auth0_provider.Auth0Provider.verify",
            new=_verify_con_superadmin,
        ), patch(
            "infrastructure.providers.auth.auth0_provider.Auth0Provider.get_user_info",
            new=AsyncMock(
                return_value={
                    "email": "admin@motogestion.com", "email_verified": True, "multifactor": [],
                }
            ),
        ):
            resp = client.post(
                "/api/auth/login",
                json={"email": "admin@motogestion.com", "token": SUPERADMIN_TOKEN, "name": "Admin"},
            )
        assert resp.status_code == 403

    def test_login_con_mfa_pasa(self, client):
        with patch(
            "infrastructure.providers.auth.auth0_provider.Auth0Provider.verify",
            new=_verify_con_superadmin,
        ), patch(
            "infrastructure.providers.auth.auth0_provider.Auth0Provider.get_user_info",
            new=AsyncMock(
                return_value={
                    "email": "admin@motogestion.com", "email_verified": True,
                    "multifactor": ["guardian"],
                }
            ),
        ):
            resp = client.post(
                "/api/auth/login",
                json={"email": "admin@motogestion.com", "token": SUPERADMIN_TOKEN, "name": "Admin"},
            )
        assert resp.status_code == 200

    def test_login_normal_no_exige_mfa_pero_si_correo_verificado(self, client, seed_talleres):
        """Un usuario sin es_super_admin no necesita MFA -- pero el correo
        verificado sí se exige para CUALQUIER login (toma de cuentas, ver
        tests/auth_login_security_test.py), así que get_user_info sí se llama."""
        with patch(
            "infrastructure.providers.auth.auth0_provider.Auth0Provider.get_user_info",
            new=AsyncMock(
                return_value={"email": f"user{TALLER_A}@test.local", "email_verified": True}
            ),
        ):
            seed = seed_talleres[TALLER_A]
            resp = client.post(
                "/api/auth/login",
                json={
                    "email": f"user{TALLER_A}@test.local",
                    "token": "test-token-taller-a",
                    "name": "Usuario De Prueba",
                },
            )
        assert resp.status_code == 200
        assert seed.documento_usuario  # sanity: el seed sigue disponible


class TestMetricasPorTenantNoSeMezclan:
    async def test_cada_taller_ve_sus_propias_metricas(self, db_conn, seed_talleres):
        # TALLER_B recibe una segunda orden para que A y B NO queden simétricos --
        # si el loop de set_tenant tuviera una fuga, un conteo igual en ambos no
        # probaría nada.
        with db_conn.cursor() as cur:
            cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(TALLER_B),))
            cur.execute(
                "INSERT INTO ordenes_trabajo (cod_taller, consecutivo_ot, fecha_elaboracion_ot, "
                "kilometraje_ingreso_ot, placa_mot_ot, documento_usu_rp_ot, documento_usu_mc_ot, "
                "cod_ot_est_ot) VALUES (%s, 99, CURRENT_DATE, 1000, %s, %s, %s, 1)",
                (TALLER_B, seed_talleres[TALLER_B].placa_moto,
                 seed_talleres[TALLER_B].documento_usuario, seed_talleres[TALLER_B].documento_usuario),
            )
        try:
            metricas = await MetricasServicio().metricas_de_todos_los_talleres()
            assert metricas[TALLER_A]["ordenes_7d"] == 1
            assert metricas[TALLER_B]["ordenes_7d"] == 2
            assert metricas[TALLER_A]["usuarios_activos"] == 1
            assert metricas[TALLER_B]["usuarios_activos"] == 1
        finally:
            with db_conn.cursor() as cur:
                cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(TALLER_B),))
                cur.execute(
                    "DELETE FROM ordenes_trabajo WHERE cod_taller = %s AND consecutivo_ot = 99",
                    (TALLER_B,),
                )


class TestAccionesSobreUnTallerExigenMotivoYQuedanEnAuditoria:
    def test_extender_prueba_en_taller_activo_rechaza(self, client, seed_talleres, superadmin_headers):
        seed = seed_talleres[TALLER_A]
        resp = client.post(
            f"/api/superadmin/talleres/{TALLER_A}/extender-prueba",
            json={"dias": 15, "motivo": "prueba de test"},
            headers=superadmin_headers,
        )
        assert resp.status_code == 400, resp.text
        assert seed.cod_taller == TALLER_A  # sanity

    def test_sin_motivo_falla_validacion(self, client, seed_talleres, superadmin_headers):
        resp = client.put(
            f"/api/superadmin/talleres/{TALLER_A}/precio",
            json={"precioSuscTal": 55000},
            headers=superadmin_headers,
        )
        assert resp.status_code == 422

    def test_ajustar_precio_actualiza_y_audita(self, client, db_conn, seed_talleres, superadmin_headers):
        resp = client.put(
            f"/api/superadmin/talleres/{TALLER_A}/precio",
            json={"precioSuscTal": 55000, "motivo": "negociación especial"},
            headers=superadmin_headers,
        )
        assert resp.status_code == 200, resp.text

        with db_conn.cursor() as cur:
            cur.execute("SELECT precio_susc_tal FROM talleres WHERE cod_taller = %s", (TALLER_A,))
            assert cur.fetchone()[0] == 55000

            cur.execute(
                "SELECT usuario, accion, motivo FROM auditoria_superadmin "
                "WHERE cod_taller = %s ORDER BY fecha DESC LIMIT 1",
                (TALLER_A,),
            )
            fila = cur.fetchone()
            assert fila is not None
            assert fila[1] == "ajustar_precio"
            assert fila[2] == "negociación especial"

    def test_suspender_y_reactivar(self, client, db_conn, seed_talleres, superadmin_headers):
        resp = client.post(
            f"/api/superadmin/talleres/{TALLER_A}/suspender",
            json={"motivo": "falta de pago"},
            headers=superadmin_headers,
        )
        assert resp.status_code == 200, resp.text
        with db_conn.cursor() as cur:
            cur.execute("SELECT estado_tal FROM talleres WHERE cod_taller = %s", (TALLER_A,))
            assert cur.fetchone()[0] == "suspendido"

        resp = client.post(
            f"/api/superadmin/talleres/{TALLER_A}/reactivar",
            json={"motivo": "pagó"},
            headers=superadmin_headers,
        )
        assert resp.status_code == 200, resp.text
        with db_conn.cursor() as cur:
            cur.execute("SELECT estado_tal FROM talleres WHERE cod_taller = %s", (TALLER_A,))
            assert cur.fetchone()[0] == "activo"

            cur.execute(
                "SELECT count(*) FROM auditoria_superadmin WHERE cod_taller = %s AND accion IN ('suspender','reactivar')",
                (TALLER_A,),
            )
            assert cur.fetchone()[0] == 2

    def test_pago_manual_activa_suscripcion_y_registra_pago(self, client, db_conn, seed_talleres, superadmin_headers):
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT fecha_fin_susc_tal FROM talleres WHERE cod_taller = %s", (TALLER_A,)
            )
            fecha_antes = cur.fetchone()[0]

        resp = client.post(
            f"/api/superadmin/talleres/{TALLER_A}/pago-manual",
            json={"monto": 49000, "detalleMedio": "Nequi", "motivo": "pago por fuera de Wompi"},
            headers=superadmin_headers,
        )
        assert resp.status_code == 200, resp.text

        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT estado_tal, fecha_fin_susc_tal FROM talleres WHERE cod_taller = %s", (TALLER_A,)
            )
            estado, fecha_despues = cur.fetchone()
            assert estado == "activo"
            assert fecha_despues is not None
            if fecha_antes is not None:
                assert fecha_despues > fecha_antes

            cur.execute(
                "SELECT medio, detalle_medio, estado FROM pagos "
                "WHERE cod_taller = %s AND medio = 'MANUAL' ORDER BY fecha DESC LIMIT 1",
                (TALLER_A,),
            )
            fila = cur.fetchone()
            assert fila == ("MANUAL", "Nequi", "APPROVED")
