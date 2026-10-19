"""F1-06: marcar un ítem de una orden como "no se cobra" (cortesía) exige el
permiso `marcar_no_cobro:ordenes-trabajo`, que NINGÚN perfil recibe por
defecto salvo Administrador (bypass de rol) -- ni siquiera Mecánico, a
propósito (control de fraude: alguien debe poder auditar/limitar quién da
cortesías). El gateo es condicional al contenido del body: un Mecánico sin
el permiso puede seguir creando/editando líneas normales (cobrar_deto=True),
solo se bloquea si intenta mandar cobrar_deto=False."""
from unittest.mock import patch

import pytest

from domain.models.auth.user_model import UserPermissionsModel
from tests.conftest import TALLER_A, _SUB_POR_TOKEN, auth_headers

pytestmark = pytest.mark.db

MECANICO_TOKEN = "test-token-taller-a-mecanico-f106"
MECANICO_SUB = "test|taller-a-mecanico-f106"
MECANICO_DOCUMENTO = "900100299"

PERMISOS_BASE_MECANICO = [
    "leer:productos", "leer:ordenes-trabajo", "crear:ordenes-trabajo", "actualizar:ordenes-trabajo",
]


@pytest.fixture
def mecanico_headers(db_conn, seed_talleres):
    """Mecánico real en TALLER_A con los permisos normales de órdenes de
    trabajo, pero SIN marcar_no_cobro:ordenes-trabajo."""
    cod_taller = TALLER_A
    with db_conn.cursor() as cur:
        cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(cod_taller),))
        cur.execute(
            "INSERT INTO perfiles (cod_taller, cod_rol_prf, cod_est_prf, nombre_prf) "
            "VALUES (%s, 2, 1, 'Mecanico F1-06 test') RETURNING cod_prf",
            (cod_taller,),
        )
        cod_prf = cur.fetchone()[0]

        cur.execute(
            "INSERT INTO usuarios (cod_taller, documento_usu, nombre_usu, apellido_1_usu, "
            "correo_usu, contrasena_usu, cod_tipo_usu, cod_est_usu, sub_id_usu, "
            "cod_prf_usu, cod_rol_prf_usu) "
            "VALUES (%s, %s, 'Mecanico', 'F1-06', %s, 'test', 1, 1, %s, %s, 2)",
            (cod_taller, MECANICO_DOCUMENTO, "mecanico-f106@test.local", MECANICO_SUB, cod_prf),
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
                "INSERT INTO perfiles_permisos "
                "(cod_taller, cod_prm_pp, cod_prf_pp, cod_rol_prf_pp, cod_est_pp) "
                "VALUES (%s, %s, %s, 2, 1)",
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
            "DELETE FROM detalle_orden_trabajo WHERE cod_taller = %s AND documento_usu_deto = %s",
            (cod_taller, MECANICO_DOCUMENTO),
        )
        cur.execute(
            "DELETE FROM perfiles_permisos WHERE cod_taller = %s AND cod_prf_pp = %s",
            (cod_taller, cod_prf),
        )
        cur.execute("DELETE FROM usuarios WHERE documento_usu = %s", (MECANICO_DOCUMENTO,))
        cur.execute("DELETE FROM perfiles WHERE cod_taller = %s AND cod_prf = %s", (cod_taller, cod_prf))


def _producto_bien(db_conn, stock=50):
    with db_conn.cursor() as cur:
        cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(TALLER_A),))
        cur.execute(
            "INSERT INTO productos (cod_taller, nombre_pro, stock_pro, stock_pro_min, "
            "cod_est_pro, precio_pro, tipo_pro) VALUES (%s, 'BIEN permiso test', %s, 2, 1, 20000, 'BIEN') "
            "RETURNING cod_pro",
            (TALLER_A, stock),
        )
        return cur.fetchone()[0]


def _borrar_producto(db_conn, cod_pro):
    with db_conn.cursor() as cur:
        cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(TALLER_A),))
        cur.execute("DELETE FROM detalle_orden_trabajo WHERE cod_taller=%s AND cod_pro_deto=%s", (TALLER_A, cod_pro))
        cur.execute("DELETE FROM movimientos_inventario WHERE cod_taller=%s AND cod_pro_mov=%s", (TALLER_A, cod_pro))
        cur.execute("DELETE FROM productos WHERE cod_taller=%s AND cod_pro=%s", (TALLER_A, cod_pro))


class TestSinPermisoNoPuedeMarcarCortesia:
    def test_no_puede_agregar_producto_como_cortesia(self, client, db_conn, seed_talleres, mecanico_headers):
        cod_pro = _producto_bien(db_conn)
        try:
            resp = client.post(
                f"/api/ordenes-trabajo/{seed_talleres[TALLER_A].consecutivo_ot}/productos",
                json={
                    "codProDeto": cod_pro,
                    "cantidadDeto": 1,
                    "cobrarDeto": False,
                    "motivoNoCobroDeto": "Cliente frecuente",
                },
                headers=mecanico_headers,
            )
            assert resp.status_code == 403
        finally:
            _borrar_producto(db_conn, cod_pro)

    def test_no_puede_actualizar_producto_existente_a_cortesia(self, client, db_conn, seed_talleres, mecanico_headers):
        cod_pro = _producto_bien(db_conn)
        try:
            resp_crear = client.post(
                f"/api/ordenes-trabajo/{seed_talleres[TALLER_A].consecutivo_ot}/productos",
                json={"codProDeto": cod_pro, "cantidadDeto": 1, "cobrarDeto": True},
                headers=mecanico_headers,
            )
            assert resp_crear.status_code == 200

            resp = client.patch(
                f"/api/ordenes-trabajo/{seed_talleres[TALLER_A].consecutivo_ot}/productos/{cod_pro}",
                json={"cantidadDeto": 1, "cobrarDeto": False, "motivoNoCobroDeto": "Cliente frecuente"},
                headers=mecanico_headers,
            )
            assert resp.status_code == 403
        finally:
            _borrar_producto(db_conn, cod_pro)

    def test_no_puede_crear_orden_con_item_de_cortesia(self, client, db_conn, seed_talleres, mecanico_headers):
        cod_pro = _producto_bien(db_conn)
        seed = seed_talleres[TALLER_A]
        try:
            resp = client.post(
                "/api/ordenes-trabajo",
                json={
                    "placaMotOt": seed.placa_moto,
                    "kilometrajeIngresoOt": 15500,
                    "detalles": [{
                        "codProDeto": cod_pro,
                        "cantidadDeto": 1,
                        "cobrarDeto": False,
                        "motivoNoCobroDeto": "Cliente frecuente",
                    }],
                },
                headers=mecanico_headers,
            )
            assert resp.status_code == 403
        finally:
            _borrar_producto(db_conn, cod_pro)


class TestSinPermisoSiPuedeSeguirTrabajandoNormal:
    """El gateo es condicional al body: sin el permiso de cortesía, el
    mecánico sigue pudiendo agregar/editar productos que SÍ se cobran."""

    def test_puede_agregar_producto_normal(self, client, db_conn, seed_talleres, mecanico_headers):
        cod_pro = _producto_bien(db_conn)
        try:
            resp = client.post(
                f"/api/ordenes-trabajo/{seed_talleres[TALLER_A].consecutivo_ot}/productos",
                json={"codProDeto": cod_pro, "cantidadDeto": 1, "cobrarDeto": True},
                headers=mecanico_headers,
            )
            assert resp.status_code == 200
        finally:
            _borrar_producto(db_conn, cod_pro)


def test_con_permiso_si_puede_marcar_cortesia(client, db_conn, seed_talleres, mecanico_headers):
    """Control positivo: una vez asignado el permiso, el mismo mecánico sí
    puede marcar una línea como cortesía."""
    cod_taller = TALLER_A
    with db_conn.cursor() as cur:
        cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(cod_taller),))
        cur.execute(
            "SELECT cod_prf FROM perfiles WHERE cod_taller=%s AND nombre_prf='Mecanico F1-06 test'",
            (cod_taller,),
        )
        cod_prf = cur.fetchone()[0]
        cur.execute(
            "SELECT cod_prm FROM permisos WHERE nombre_prm = 'marcar_no_cobro:ordenes-trabajo'"
        )
        cod_prm = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO perfiles_permisos (cod_taller, cod_prm_pp, cod_prf_pp, cod_rol_prf_pp, cod_est_pp) "
            "VALUES (%s, %s, %s, 2, 1)",
            (cod_taller, cod_prm, cod_prf),
        )

    cod_pro = _producto_bien(db_conn)
    try:
        resp = client.post(
            f"/api/ordenes-trabajo/{seed_talleres[TALLER_A].consecutivo_ot}/productos",
            json={
                "codProDeto": cod_pro,
                "cantidadDeto": 1,
                "cobrarDeto": False,
                "motivoNoCobroDeto": "Cliente frecuente",
            },
            headers=mecanico_headers,
        )
        assert resp.status_code == 200
    finally:
        _borrar_producto(db_conn, cod_pro)
        with db_conn.cursor() as cur:
            cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(cod_taller),))
            cur.execute(
                "DELETE FROM perfiles_permisos WHERE cod_taller=%s AND cod_prf_pp=%s AND cod_prm_pp=%s",
                (cod_taller, cod_prf, cod_prm),
            )


def test_admin_sigue_pudiendo_marcar_cortesia_sin_asignacion_explicita(client, db_conn, seed_talleres, mock_auth0):
    """Control: el Admin (bypass de rol en require_permiso/usuario_tiene_permiso)
    no necesita una fila en perfiles_permisos para marcar cortesías."""
    seed = seed_talleres[TALLER_A]
    cod_pro = _producto_bien(db_conn)
    try:
        resp = client.post(
            f"/api/ordenes-trabajo/{seed.consecutivo_ot}/productos",
            json={
                "codProDeto": cod_pro,
                "cantidadDeto": 1,
                "cobrarDeto": False,
                "motivoNoCobroDeto": "Cliente frecuente",
            },
            headers=auth_headers(TALLER_A),
        )
        assert resp.status_code == 200
    finally:
        _borrar_producto(db_conn, cod_pro)
