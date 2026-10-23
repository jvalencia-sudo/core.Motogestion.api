"""F1-08: vista móvil del mecánico. El front reutiliza endpoints de /tablero
que ya existen (PUT .../estado) y uno nuevo (PATCH .../nota) para "Necesito
repuesto" -- ambos con la MISMA regla de alcance: un mecánico sin
ver_todo:tablero solo puede actuar sobre SUS PROPIAS órdenes.

La nota se AGREGA a observacion_ot sin reemplazarla: ahí también vive el
"trabajo pedido" con el que se abrió la orden (lo que las tarjetas del
tablero muestran como "servicio")."""
from unittest.mock import patch

import pytest

from domain.models.auth.user_model import UserPermissionsModel
from tests.conftest import TALLER_A, _SUB_POR_TOKEN, auth_headers

pytestmark = [pytest.mark.db, pytest.mark.usefixtures("mock_auth0")]

MECANICO_TOKEN = "test-token-taller-a-mecanico-f108"
MECANICO_SUB = "test|taller-a-mecanico-f108"
MECANICO_DOCUMENTO = "900100499"

PERMISOS_MECANICO = ["ver:tablero", "crear_editar:ordenes-trabajo"]


@pytest.fixture
def mecanico_headers(db_conn, seed_talleres):
    """Mecánico real en TALLER_A, SIN ver_todo:tablero -- igual a lo que
    fn_seed_perfiles_taller le da a un Mecánico real."""
    cod_taller = TALLER_A
    with db_conn.cursor() as cur:
        cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(cod_taller),))
        cur.execute(
            "INSERT INTO perfiles (cod_taller, es_admin, cod_est_prf, nombre_prf) "
            "VALUES (%s, false, 1, 'Mecanico F1-08 test') RETURNING cod_prf",
            (cod_taller,),
        )
        cod_prf = cur.fetchone()[0]

        cur.execute(
            "INSERT INTO usuarios (cod_taller, documento_usu, nombre_usu, apellido_1_usu, "
            "correo_usu, contrasena_usu, cod_tipo_usu, cod_est_usu, sub_id_usu, "
            "cod_prf_usu, es_admin_usu) "
            "VALUES (%s, %s, 'Mecanico', 'F1-08', %s, 'test', 1, 1, %s, %s, false)",
            (cod_taller, MECANICO_DOCUMENTO, "mecanico-f108@test.local", MECANICO_SUB, cod_prf),
        )

        cur.execute(
            "SELECT cod_prm FROM permisos WHERE nombre_prm = ANY(%s)",
            (PERMISOS_MECANICO,),
        )
        cods_prm = [row[0] for row in cur.fetchall()]
        assert len(cods_prm) == len(PERMISOS_MECANICO), (
            "El catálogo de permisos no tiene alguno de los nombres esperados."
        )
        for cod_prm in cods_prm:
            cur.execute(
                "INSERT INTO perfiles_permisos (cod_taller, cod_prm_pp, cod_prf_pp, cod_est_pp) "
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


@pytest.fixture
def orden_del_mecanico(db_conn, seed_talleres, mecanico_headers):
    """Reasigna la OT sembrada (hoy del admin de prueba) al mecánico de este
    módulo, con una observación inicial reconocible ("trabajo pedido"), y la
    deja en Pendiente. Se restaura al terminar para no afectar otros tests
    de este módulo que comparten la misma OT sembrada.

    Depende de `mecanico_headers` aunque no use el valor: ese fixture es el
    que inserta la fila en `usuarios` a la que `documento_usu_mc_ot` debe
    apuntar (si no, la FK fk_ot_mecanico revienta)."""
    seed = seed_talleres[TALLER_A]
    with db_conn.cursor() as cur:
        cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(TALLER_A),))
        cur.execute(
            "UPDATE ordenes_trabajo SET documento_usu_mc_ot = %s, cod_ot_est_ot = 1, "
            "observacion_ot = 'Cambio de aceite y filtro' "
            "WHERE cod_taller = %s AND consecutivo_ot = %s",
            (MECANICO_DOCUMENTO, TALLER_A, seed.consecutivo_ot),
        )
    yield seed
    with db_conn.cursor() as cur:
        cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(TALLER_A),))
        cur.execute(
            "UPDATE ordenes_trabajo SET documento_usu_mc_ot = %s, cod_ot_est_ot = 1, "
            "observacion_ot = NULL "
            "WHERE cod_taller = %s AND consecutivo_ot = %s",
            (seed.documento_usuario, TALLER_A, seed.consecutivo_ot),
        )


class TestNotaAgregaSinReemplazar:
    def test_mecanico_agrega_nota_a_su_propia_orden(self, client, mecanico_headers, orden_del_mecanico):
        seed = orden_del_mecanico
        resp = client.patch(
            f"/api/tablero/{seed.consecutivo_ot}/nota",
            json={"nota": "Necesito repuesto: pastillas de freno"},
            headers=mecanico_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["consecutivoOt"] == seed.consecutivo_ot
        # No reemplaza el trabajo pedido original -- lo conserva y agrega la nota.
        assert "Cambio de aceite y filtro" in data["observacionOt"]
        assert "Necesito repuesto: pastillas de freno" in data["observacionOt"]

    def test_mecanico_no_puede_agregar_nota_a_orden_ajena(self, client, mecanico_headers, seed_talleres):
        """La OT sembrada sigue asignada al admin de prueba (no se usó la
        fixture orden_del_mecanico) -- el mecánico no es su dueño."""
        seed = seed_talleres[TALLER_A]
        resp = client.patch(
            f"/api/tablero/{seed.consecutivo_ot}/nota",
            json={"nota": "Necesito repuesto: pastillas de freno"},
            headers=mecanico_headers,
        )
        assert resp.status_code == 403

    def test_admin_agrega_nota_a_orden_de_cualquier_mecanico(self, client, orden_del_mecanico):
        """El admin (ver_todo implícito por es_admin_usu) puede anotar la OT
        aunque esté asignada al mecánico, no a él."""
        seed = orden_del_mecanico
        resp = client.patch(
            f"/api/tablero/{seed.consecutivo_ot}/nota",
            json={"nota": "Revisado por el admin"},
            headers=auth_headers(TALLER_A),
        )
        assert resp.status_code == 200

    def test_nota_vacia_o_muy_corta_rechazada(self, client, mecanico_headers, orden_del_mecanico):
        seed = orden_del_mecanico
        resp = client.patch(
            f"/api/tablero/{seed.consecutivo_ot}/nota",
            json={"nota": "  "},
            headers=mecanico_headers,
        )
        assert resp.status_code == 422

    def test_orden_inexistente_404(self, client, mecanico_headers):
        resp = client.patch(
            "/api/tablero/999999/nota",
            json={"nota": "Necesito un repuesto cualquiera"},
            headers=mecanico_headers,
        )
        assert resp.status_code == 404


class TestEstadoMecanicoSoloSusOrdenes:
    """El botón "Empecé"/"Terminé" de la vista móvil reutiliza PUT
    /tablero/{id}/estado -- ya construido en F1-12, pero sin test propio
    hasta ahora. F1-08 depende de que esta regla siga sosteniéndose."""

    def test_mecanico_mueve_su_propia_orden_dentro_de_su_alcance(
        self, client, mecanico_headers, orden_del_mecanico
    ):
        seed = orden_del_mecanico
        resp = client.put(
            f"/api/tablero/{seed.consecutivo_ot}/estado",
            json={"codEstado": 2},
            headers=mecanico_headers,
        )
        assert resp.status_code == 200
        # NOTA: CambioEstadoTableroResponseContract no hereda BaseContractSchema
        # (sin alias_generator) -- la respuesta queda en snake_case, inconsistente
        # con el resto del API. Preexistente a F1-08; el front no lee este body.
        assert resp.json()["cod_estado"] == 2

    def test_mecanico_no_puede_mover_orden_ajena(self, client, mecanico_headers, seed_talleres):
        seed = seed_talleres[TALLER_A]
        resp = client.put(
            f"/api/tablero/{seed.consecutivo_ot}/estado",
            json={"codEstado": 2},
            headers=mecanico_headers,
        )
        assert resp.status_code == 403

    def test_mecanico_no_puede_entregar_directo(self, client, mecanico_headers, orden_del_mecanico):
        """Entregada (4) está fuera de ESTADOS_MECANICO -- eso es trabajo de
        recepción/admin (cobro, kilometraje de salida), no del mecánico."""
        seed = orden_del_mecanico
        resp = client.put(
            f"/api/tablero/{seed.consecutivo_ot}/estado",
            json={"codEstado": 4},
            headers=mecanico_headers,
        )
        assert resp.status_code == 403
