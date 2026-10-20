"""F0-13: el estado admin/no-admin se deriva del perfil elegido (ya no se pide
aparte), no se puede dejar un taller sin administradores activos, y la matriz
de permisos reemplaza todo de una vez (transaccional) sin poder tocar el
perfil Administrador."""

import pytest

from tests.conftest import TALLER_A, TALLER_B, auth_headers

pytestmark = [pytest.mark.db, pytest.mark.usefixtures("mock_auth0")]


class TestDerivarEsAdminDesdeElPerfil:
    def test_invitar_con_perfil_mecanico_deriva_es_admin_false(self, client, db_conn, seed_talleres, perfil_mecanico):
        resp = client.post(
            "/api/auth/invitar",
            json={"correo": "nuevo-mecanico-f013@example.com", "nombre": "Nuevo Mecanico", "cod_prf": perfil_mecanico},
            headers=auth_headers(TALLER_A),
        )
        assert resp.status_code == 201, resp.text
        documento = resp.json()["documento_usu"]
        with db_conn.cursor() as cur:
            cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(TALLER_A),))
            cur.execute(
                "SELECT cod_prf_usu, es_admin_usu FROM usuarios WHERE documento_usu=%s", (documento,)
            )
            cod_prf_usu, es_admin_usu = cur.fetchone()
            cur.execute("DELETE FROM usuarios WHERE documento_usu=%s", (documento,))
        assert cod_prf_usu == perfil_mecanico
        assert es_admin_usu is False

    def test_invitar_con_perfil_de_otro_taller_falla(self, client, db_conn, seed_talleres):
        with db_conn.cursor() as cur:
            cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(TALLER_B),))
            cur.execute(
                "INSERT INTO perfiles (cod_taller, es_admin, cod_est_prf, nombre_prf) "
                "VALUES (%s, false, 1, 'Mecanico de B') RETURNING cod_prf",
                (TALLER_B,),
            )
            cod_prf_de_b = cur.fetchone()[0]
        try:
            resp = client.post(
                "/api/auth/invitar",
                json={"correo": "intento-cross-tenant@example.com", "nombre": "Intento", "cod_prf": cod_prf_de_b},
                headers=auth_headers(TALLER_A),
            )
            assert resp.status_code == 404
        finally:
            with db_conn.cursor() as cur:
                cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(TALLER_B),))
                cur.execute("DELETE FROM perfiles WHERE cod_taller=%s AND cod_prf=%s", (TALLER_B, cod_prf_de_b))


class TestUltimoAdministrador:
    def test_no_puede_desactivar_al_unico_admin(self, client, db_conn, seed_talleres):
        seed = seed_talleres[TALLER_A]
        try:
            resp = client.delete(
                f"/api/admin/users/{seed.documento_usuario}", headers=auth_headers(TALLER_A)
            )
            assert resp.status_code == 400
        finally:
            # Si el guard tuviera un regresión y la desactivación sí pasara, que
            # este test no deje la BD sucia para los que corren después.
            with db_conn.cursor() as cur:
                cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(TALLER_A),))
                cur.execute(
                    "UPDATE usuarios SET cod_est_usu = 1 WHERE documento_usu = %s",
                    (seed.documento_usuario,),
                )

    def test_con_dos_admins_si_puede_desactivar_uno(self, client, db_conn, seed_talleres):
        seed = seed_talleres[TALLER_A]
        cod_taller = TALLER_A
        with db_conn.cursor() as cur:
            cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(cod_taller),))
            cur.execute(
                "SELECT cod_prf FROM perfiles WHERE cod_taller=%s AND es_admin=true LIMIT 1", (cod_taller,)
            )
            cod_prf_admin = cur.fetchone()[0]
            cur.execute(
                "INSERT INTO usuarios (cod_taller, documento_usu, nombre_usu, apellido_1_usu, "
                "correo_usu, contrasena_usu, cod_tipo_usu, cod_est_usu, sub_id_usu, "
                "cod_prf_usu, es_admin_usu) "
                "VALUES (%s, %s, 'Segundo', 'Admin', %s, 'test', 1, 1, NULL, %s, true)",
                (cod_taller, "900100299", "segundo-admin-f013@test.local", cod_prf_admin),
            )
        try:
            resp = client.delete(
                f"/api/admin/users/{seed.documento_usuario}", headers=auth_headers(TALLER_A)
            )
            assert resp.status_code == 200, resp.text
        finally:
            with db_conn.cursor() as cur:
                cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(cod_taller),))
                cur.execute("UPDATE usuarios SET cod_est_usu = 1 WHERE documento_usu = %s", (seed.documento_usuario,))
                cur.execute("DELETE FROM usuarios WHERE documento_usu = %s", ("900100299",))


class TestReemplazarPermisosDeUnPerfil:
    def test_reemplaza_permisos_en_una_transaccion_y_queda_en_auditoria(
        self, client, db_conn, seed_talleres, perfil_mecanico
    ):
        with db_conn.cursor() as cur:
            cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(TALLER_A),))
            cur.execute(
                "SELECT cod_prm FROM permisos WHERE nombre_prm IN ('ver:clientes', 'crear_editar:clientes')"
            )
            cod_prm_list = [row[0] for row in cur.fetchall()]
        assert len(cod_prm_list) == 2

        resp = client.put(
            f"/api/perfil-permiso/perfil/{perfil_mecanico}/permisos",
            json={"cod_prm_list": cod_prm_list},
            headers=auth_headers(TALLER_A),
        )
        assert resp.status_code == 200, resp.text

        with db_conn.cursor() as cur:
            cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(TALLER_A),))
            cur.execute(
                "SELECT cod_prm_pp FROM perfiles_permisos WHERE cod_taller=%s AND cod_prf_pp=%s",
                (TALLER_A, perfil_mecanico),
            )
            asignados = {row[0] for row in cur.fetchall()}
            assert asignados == set(cod_prm_list)

            cur.execute(
                "SELECT tabla, evento FROM audit_log WHERE cod_taller=%s AND tabla='perfiles_permisos' "
                "ORDER BY fecha DESC LIMIT 1",
                (TALLER_A,),
            )
            fila_auditoria = cur.fetchone()
            assert fila_auditoria is not None
            assert fila_auditoria == ("perfiles_permisos", "U")

    def test_no_se_puede_editar_el_perfil_administrador(self, client, db_conn, seed_talleres):
        with db_conn.cursor() as cur:
            cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(TALLER_A),))
            cur.execute(
                "SELECT cod_prf FROM perfiles WHERE cod_taller=%s AND es_admin=true LIMIT 1", (TALLER_A,)
            )
            cod_prf_admin = cur.fetchone()[0]

        resp = client.put(
            f"/api/perfil-permiso/perfil/{cod_prf_admin}/permisos",
            json={"cod_prm_list": []},
            headers=auth_headers(TALLER_A),
        )
        assert resp.status_code == 400
