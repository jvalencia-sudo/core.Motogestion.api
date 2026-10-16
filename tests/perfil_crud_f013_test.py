"""F0-13 (ext): roles propios del taller -- crear (desde cero o duplicando
permisos de otro), renombrar y eliminar perfiles, con las validaciones que
antes no existían: nombre único por taller, máximo 10, el perfil nuevo nunca
puede quedar con trato de Administrador, y no se elimina un perfil con
usuarios asignados."""

import pytest

from tests.conftest import TALLER_A, TALLER_B, auth_headers

pytestmark = [pytest.mark.db, pytest.mark.usefixtures("mock_auth0")]


def _cod_prf_admin(db_conn, cod_taller: int) -> int:
    with db_conn.cursor() as cur:
        cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(cod_taller),))
        cur.execute(
            "SELECT cod_prf FROM perfiles WHERE cod_taller=%s AND cod_rol_prf=1 LIMIT 1", (cod_taller,)
        )
        return cur.fetchone()[0]


def _borrar_perfil(db_conn, cod_taller: int, cod_prf: int) -> None:
    with db_conn.cursor() as cur:
        cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(cod_taller),))
        cur.execute(
            "DELETE FROM perfiles_permisos WHERE cod_taller=%s AND cod_prf_pp=%s", (cod_taller, cod_prf)
        )
        cur.execute("DELETE FROM usuarios WHERE cod_taller=%s AND cod_prf_usu=%s", (cod_taller, cod_prf))
        cur.execute("DELETE FROM perfiles WHERE cod_taller=%s AND cod_prf=%s", (cod_taller, cod_prf))


class TestCrearPerfil:
    def test_crea_perfil_desde_cero_sin_permisos(self, client, db_conn, seed_talleres):
        resp = client.post(
            "/api/perfil",
            json={"nombre_prf": "Practicante", "descripcion_prf": "Solo lectura de ordenes"},
            headers=auth_headers(TALLER_A),
        )
        assert resp.status_code == 201, resp.text
        cod_prf = resp.json()["cod_prf"]
        try:
            with db_conn.cursor() as cur:
                cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(TALLER_A),))
                cur.execute("SELECT cod_rol_prf FROM perfiles WHERE cod_prf=%s", (cod_prf,))
                assert cur.fetchone()[0] == 2
                cur.execute(
                    "SELECT COUNT(*) FROM perfiles_permisos WHERE cod_prf_pp=%s", (cod_prf,)
                )
                assert cur.fetchone()[0] == 0
        finally:
            _borrar_perfil(db_conn, TALLER_A, cod_prf)

    def test_crea_perfil_duplicando_permisos_de_otro(self, client, db_conn, seed_talleres, perfil_mecanico):
        with db_conn.cursor() as cur:
            cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(TALLER_A),))
            cur.execute(
                "SELECT cod_prm FROM permisos WHERE nombre_prm IN ('leer:clientes', 'crear:clientes')"
            )
            cod_prm_list = {row[0] for row in cur.fetchall()}
        assert len(cod_prm_list) == 2
        resp_matriz = client.put(
            f"/api/perfil-permiso/perfil/{perfil_mecanico}/permisos",
            json={"cod_prm_list": list(cod_prm_list)},
            headers=auth_headers(TALLER_A),
        )
        assert resp_matriz.status_code == 200, resp_matriz.text

        resp = client.post(
            "/api/perfil",
            json={
                "nombre_prf": "Practicante Duplicado",
                "descripcion_prf": "Copia de mecanico",
                "duplicar_de": perfil_mecanico,
            },
            headers=auth_headers(TALLER_A),
        )
        assert resp.status_code == 201, resp.text
        cod_prf = resp.json()["cod_prf"]
        try:
            with db_conn.cursor() as cur:
                cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(TALLER_A),))
                cur.execute(
                    "SELECT cod_prm_pp FROM perfiles_permisos WHERE cod_prf_pp=%s", (cod_prf,)
                )
                copiados = {row[0] for row in cur.fetchall()}
            assert copiados == cod_prm_list
        finally:
            _borrar_perfil(db_conn, TALLER_A, cod_prf)

    def test_rechaza_nombre_duplicado_case_insensitive(self, client, db_conn, seed_talleres):
        resp1 = client.post(
            "/api/perfil",
            json={"nombre_prf": "Vendedor", "descripcion_prf": "Vende repuestos"},
            headers=auth_headers(TALLER_A),
        )
        assert resp1.status_code == 201, resp1.text
        cod_prf = resp1.json()["cod_prf"]
        try:
            resp2 = client.post(
                "/api/perfil",
                json={"nombre_prf": "  VENDEDOR  ", "descripcion_prf": "Otro"},
                headers=auth_headers(TALLER_A),
            )
            assert resp2.status_code == 400
        finally:
            _borrar_perfil(db_conn, TALLER_A, cod_prf)

    def test_rechaza_perfil_numero_11(self, client, db_conn, seed_talleres):
        # El seed de test ya deja 1 perfil ("Admin de prueba"): 9 mas llegan a 10.
        creados = []
        try:
            for i in range(9):
                resp = client.post(
                    "/api/perfil",
                    json={"nombre_prf": f"Rol extra {i}", "descripcion_prf": "x"},
                    headers=auth_headers(TALLER_A),
                )
                assert resp.status_code == 201, resp.text
                creados.append(resp.json()["cod_prf"])

            resp_11 = client.post(
                "/api/perfil",
                json={"nombre_prf": "Rol numero 11", "descripcion_prf": "x"},
                headers=auth_headers(TALLER_A),
            )
            assert resp_11.status_code == 400
        finally:
            for cod_prf in creados:
                _borrar_perfil(db_conn, TALLER_A, cod_prf)

    def test_nuevo_perfil_nunca_es_administrador(self, client, db_conn, seed_talleres):
        resp = client.post(
            "/api/perfil",
            json={"nombre_prf": "Casi admin", "descripcion_prf": "x", "cod_rol_prf": 1},
            headers=auth_headers(TALLER_A),
        )
        assert resp.status_code == 201, resp.text
        cod_prf = resp.json()["cod_prf"]
        try:
            with db_conn.cursor() as cur:
                cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(TALLER_A),))
                cur.execute("SELECT cod_rol_prf FROM perfiles WHERE cod_prf=%s", (cod_prf,))
                assert cur.fetchone()[0] == 2
        finally:
            _borrar_perfil(db_conn, TALLER_A, cod_prf)

    def test_duplicar_de_perfil_de_otro_taller_falla(self, client, db_conn, seed_talleres):
        with db_conn.cursor() as cur:
            cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(TALLER_B),))
            cur.execute(
                "INSERT INTO perfiles (cod_taller, cod_rol_prf, cod_est_prf, nombre_prf) "
                "VALUES (%s, 2, 1, 'Mecanico de B') RETURNING cod_prf",
                (TALLER_B,),
            )
            cod_prf_de_b = cur.fetchone()[0]
        try:
            resp = client.post(
                "/api/perfil",
                json={"nombre_prf": "Intento cross tenant", "descripcion_prf": "x", "duplicar_de": cod_prf_de_b},
                headers=auth_headers(TALLER_A),
            )
            assert resp.status_code == 404
        finally:
            _borrar_perfil(db_conn, TALLER_B, cod_prf_de_b)

    def test_rechaza_nombre_vacio_o_solo_espacios(self, client, seed_talleres):
        resp = client.post(
            "/api/perfil",
            json={"nombre_prf": "   ", "descripcion_prf": "x"},
            headers=auth_headers(TALLER_A),
        )
        assert resp.status_code == 422


class TestActualizarPerfil:
    def test_renombra_perfil_propio(self, client, db_conn, seed_talleres, perfil_mecanico):
        resp = client.put(
            "/api/perfil",
            json={
                "cod_prf": perfil_mecanico,
                "nombre_prf": "Mecanico Senior",
                "descripcion_prf": "Con mas permisos",
            },
            headers=auth_headers(TALLER_A),
        )
        assert resp.status_code == 200, resp.text
        with db_conn.cursor() as cur:
            cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(TALLER_A),))
            cur.execute("SELECT nombre_prf FROM perfiles WHERE cod_prf=%s", (perfil_mecanico,))
            assert cur.fetchone()[0] == "Mecanico Senior"

    def test_no_se_puede_renombrar_el_perfil_administrador(self, client, db_conn, seed_talleres):
        cod_prf_admin = _cod_prf_admin(db_conn, TALLER_A)
        resp = client.put(
            "/api/perfil",
            json={"cod_prf": cod_prf_admin, "nombre_prf": "Otro nombre", "descripcion_prf": "x"},
            headers=auth_headers(TALLER_A),
        )
        assert resp.status_code == 400

    def test_rechaza_nombre_duplicado_al_renombrar(self, client, db_conn, seed_talleres, perfil_mecanico):
        # "Admin de prueba" es el nombre del perfil admin sembrado por seed_talleres.
        resp = client.put(
            "/api/perfil",
            json={"cod_prf": perfil_mecanico, "nombre_prf": "admin DE prueba", "descripcion_prf": "x"},
            headers=auth_headers(TALLER_A),
        )
        assert resp.status_code == 400

    def test_no_permite_cambiar_rol_via_update(self, client, db_conn, seed_talleres, perfil_mecanico):
        resp = client.put(
            "/api/perfil",
            json={
                "cod_prf": perfil_mecanico,
                "nombre_prf": "Mecanico F0-13 test",
                "descripcion_prf": "x",
                "cod_rol_prf": 1,
            },
            headers=auth_headers(TALLER_A),
        )
        assert resp.status_code == 200, resp.text
        with db_conn.cursor() as cur:
            cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(TALLER_A),))
            cur.execute("SELECT cod_rol_prf FROM perfiles WHERE cod_prf=%s", (perfil_mecanico,))
            assert cur.fetchone()[0] == 2


class TestEliminarPerfil:
    def test_elimina_perfil_sin_usuarios(self, client, db_conn, seed_talleres):
        resp_crear = client.post(
            "/api/perfil",
            json={"nombre_prf": "Desechable", "descripcion_prf": "x"},
            headers=auth_headers(TALLER_A),
        )
        cod_prf = resp_crear.json()["cod_prf"]

        resp = client.delete(f"/api/perfil/{cod_prf}", headers=auth_headers(TALLER_A))
        assert resp.status_code == 204, resp.text

        with db_conn.cursor() as cur:
            cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(TALLER_A),))
            cur.execute("SELECT COUNT(*) FROM perfiles WHERE cod_prf=%s", (cod_prf,))
            assert cur.fetchone()[0] == 0

    def test_rechaza_eliminar_perfil_con_usuarios_asignados(
        self, client, db_conn, seed_talleres, perfil_mecanico
    ):
        with db_conn.cursor() as cur:
            cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(TALLER_A),))
            cur.execute(
                "INSERT INTO usuarios (cod_taller, documento_usu, nombre_usu, apellido_1_usu, "
                "correo_usu, contrasena_usu, cod_tipo_usu, cod_est_usu, sub_id_usu, "
                "cod_prf_usu, cod_rol_prf_usu) "
                "VALUES (%s, %s, 'Con', 'Perfil', %s, 'test', 1, 1, NULL, %s, 2)",
                (TALLER_A, "900100300", "usuario-con-perfil-f013@test.local", perfil_mecanico),
            )
        try:
            resp = client.delete(f"/api/perfil/{perfil_mecanico}", headers=auth_headers(TALLER_A))
            assert resp.status_code == 400

            with db_conn.cursor() as cur:
                cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(TALLER_A),))
                cur.execute("SELECT COUNT(*) FROM perfiles WHERE cod_prf=%s", (perfil_mecanico,))
                assert cur.fetchone()[0] == 1
        finally:
            with db_conn.cursor() as cur:
                cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(TALLER_A),))
                cur.execute("DELETE FROM usuarios WHERE documento_usu=%s", ("900100300",))

    def test_no_se_puede_eliminar_el_perfil_administrador(self, client, db_conn, seed_talleres):
        cod_prf_admin = _cod_prf_admin(db_conn, TALLER_A)
        resp = client.delete(f"/api/perfil/{cod_prf_admin}", headers=auth_headers(TALLER_A))
        assert resp.status_code == 400

    def test_eliminar_perfil_de_otro_taller_falla_404(self, client, db_conn, seed_talleres):
        with db_conn.cursor() as cur:
            cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(TALLER_B),))
            cur.execute(
                "INSERT INTO perfiles (cod_taller, cod_rol_prf, cod_est_prf, nombre_prf) "
                "VALUES (%s, 2, 1, 'Perfil de B') RETURNING cod_prf",
                (TALLER_B,),
            )
            cod_prf_de_b = cur.fetchone()[0]
        try:
            resp = client.delete(f"/api/perfil/{cod_prf_de_b}", headers=auth_headers(TALLER_A))
            assert resp.status_code == 404
        finally:
            _borrar_perfil(db_conn, TALLER_B, cod_prf_de_b)
