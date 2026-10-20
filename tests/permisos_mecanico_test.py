"""F0-11: matriz de permisos con un usuario Mecánico real (perfil + permisos
sembrados en BD, no un mock). Antes de este ticket, un mecánico podía borrar
productos/clientes/motos/marcas y tocar endpoints de administración con solo tener
un token válido -- el backend no revisaba nada de esto. Reproduce exactamente los 3
hallazgos citados en el ticket (asignarse permisos, borrar un producto sin permiso)
más la cobertura equivalente en clientes/motos/marcas/admin."""
from unittest.mock import patch

import pytest

from domain.models.auth.user_model import UserPermissionsModel
from tests.conftest import TALLER_A, _SUB_POR_TOKEN, auth_headers

pytestmark = pytest.mark.db

MECANICO_TOKEN = "test-token-taller-a-mecanico"
MECANICO_SUB = "test|taller-a-mecanico"
MECANICO_DOCUMENTO = "900100199"

# Mismo subconjunto que fn_seed_perfiles_taller le da al perfil Mecánico
# en el esquema real -- no son permisos inventados para el test.
PERMISOS_MECANICO = [
    "ver:clientes", "ver:marcas", "ver:motos", "ver:productos",
    "ver:ordenes-trabajo", "crear_editar:ordenes-trabajo",
    "ver:tablero", "ver:reclamos", "crear_editar:reclamos",
]


@pytest.fixture
def mecanico_headers(db_conn, seed_talleres):
    """Siembra un usuario Mecánico real en TALLER_A (perfil propio + permisos
    activos del subconjunto de arriba) y parcha Auth0Provider.verify para que su
    token de prueba resuelva a ese sub. Limpia todo al terminar."""
    cod_taller = TALLER_A
    with db_conn.cursor() as cur:
        cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(cod_taller),))
        cur.execute(
            "INSERT INTO perfiles (cod_taller, es_admin, cod_est_prf, nombre_prf) "
            "VALUES (%s, false, 1, 'Mecánico de prueba') RETURNING cod_prf",
            (cod_taller,),
        )
        cod_prf = cur.fetchone()[0]

        cur.execute(
            "INSERT INTO usuarios (cod_taller, documento_usu, nombre_usu, apellido_1_usu, "
            "correo_usu, contrasena_usu, cod_tipo_usu, cod_est_usu, sub_id_usu, "
            "cod_prf_usu, es_admin_usu) "
            "VALUES (%s, %s, 'Mecanico', 'De Prueba', %s, 'test', 1, 1, %s, %s, false)",
            (cod_taller, MECANICO_DOCUMENTO, "mecanico-f011@test.local", MECANICO_SUB, cod_prf),
        )

        cur.execute(
            "SELECT cod_prm FROM permisos WHERE nombre_prm = ANY(%s)",
            (PERMISOS_MECANICO,),
        )
        cods_prm = [row[0] for row in cur.fetchall()]
        assert len(cods_prm) == len(PERMISOS_MECANICO), (
            "El catálogo de permisos no tiene alguno de los nombres esperados -- "
            "revisa que el esquema de test esté actualizado."
        )
        for cod_prm in cods_prm:
            cur.execute(
                "INSERT INTO perfiles_permisos "
                "(cod_taller, cod_prm_pp, cod_prf_pp, cod_est_pp) "
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


class TestMecanicoNoPuedeMutarLoQueNoLeFueAsignado:
    """Reproduce el hallazgo del ticket: un mecánico borrando productos (y, por
    extensión, clientes/motos/marcas) sin tener 'eliminar:*' asignado."""

    def test_no_puede_eliminar_producto(self, client, seed_talleres, mecanico_headers):
        seed = seed_talleres[TALLER_A]
        resp = client.delete(f"/api/productos/{seed.cod_producto}", headers=mecanico_headers)
        assert resp.status_code == 403

    def test_no_puede_eliminar_cliente(self, client, seed_talleres, mecanico_headers):
        seed = seed_talleres[TALLER_A]
        resp = client.delete(f"/api/clientes/{seed.documento_cliente}", headers=mecanico_headers)
        assert resp.status_code == 403

    def test_no_puede_eliminar_moto(self, client, seed_talleres, mecanico_headers):
        seed = seed_talleres[TALLER_A]
        resp = client.delete(f"/api/motos/{seed.placa_moto}", headers=mecanico_headers)
        assert resp.status_code == 403

    def test_no_puede_eliminar_marca(self, client, seed_talleres, mecanico_headers):
        seed = seed_talleres[TALLER_A]
        resp = client.delete(f"/api/marcas/{seed.cod_marca}", headers=mecanico_headers)
        assert resp.status_code == 403

    def test_no_puede_crear_producto(self, client, mecanico_headers):
        resp = client.post(
            "/api/productos",
            json={
                "nombre_pro": "Intento sin permiso",
                "descripcion_pro": "x",
                "stock_pro": 1,
                "stock_pro_min": 0,
                "precio_pro": 1000,
            },
            headers=mecanico_headers,
        )
        assert resp.status_code == 403


class TestMecanicoNoPuedeAsignarsePermisos:
    """Reproduce el hallazgo del ticket: un mecánico asignándose a sí mismo
    'eliminar:productos' con POST /perfil-permiso/asignar."""

    def test_no_puede_asignarse_permisos(self, client, seed_talleres, mecanico_headers):
        resp = client.post(
            "/api/perfil-permiso/asignar",
            json={"cod_prf": 1, "cod_prm": 1},
            headers=mecanico_headers,
        )
        assert resp.status_code == 403

    def test_no_puede_listar_perfiles(self, client, mecanico_headers):
        assert client.get("/api/perfil", headers=mecanico_headers).status_code == 403

    def test_no_puede_crear_usuario_admin(self, client, mecanico_headers):
        resp = client.post(
            "/api/admin/users",
            json={
                "documento_usu": "999999999",
                "nombre_usu": "Intento",
                "apellido_1_usu": "Sin Permiso",
                "correo_usu": "intento@test.local",
                "password": "clave12345",
                "cod_prf_usu": 1,
                "cod_tipo_usu": 2,
                "cod_est_usu": 1,
            },
            headers=mecanico_headers,
        )
        assert resp.status_code == 403

    def test_no_puede_editar_config_de_mi_taller(self, client, mecanico_headers):
        """F0-13 (cierre): 'Mi taller' (PUT /talleres/config) exige require_admin --
        un mecánico no puede tocar mano de obra, comprobante ni garantía del taller."""
        resp = client.put(
            "/api/talleres/config",
            json={"modo_mano_obra": "HORAS", "tarifa_hora_pred": 99999},
            headers=mecanico_headers,
        )
        assert resp.status_code == 403


class TestMecanicoSiPuedeHacerLoQueSeLeAsigno:
    """El objetivo no es bloquear todo: el mecánico sigue pudiendo trabajar con lo
    que su perfil sí le concede (crear/actualizar:ordenes-trabajo)."""

    def test_puede_crear_orden_de_trabajo(self, client, seed_talleres, mecanico_headers):
        seed = seed_talleres[TALLER_A]
        resp = client.post(
            "/api/ordenes-trabajo",
            json={
                "placa_mot_ot": seed.placa_moto,
                "kilometraje_ingreso_ot": 15500,
                "documento_usu_rp_ot": seed.documento_usuario,
                "documento_usu_mc_ot": seed.documento_usuario,
            },
            headers=mecanico_headers,
        )
        assert resp.status_code == 201

    def test_puede_leer_productos(self, client, mecanico_headers):
        assert client.get("/api/productos", headers=mecanico_headers).status_code == 200


def test_admin_sigue_pudiendo_todo(client, seed_talleres, mock_auth0):
    """Control: el Admin (seed_talleres ya lo crea con es_admin_usu=true) sigue
    pasando sin consultar perfiles_permisos -- no es una regresión para él."""
    seed = seed_talleres[TALLER_A]
    resp = client.get(f"/api/productos/{seed.cod_producto}", headers=auth_headers(TALLER_A))
    assert resp.status_code == 200
