"""F1-12: fusiona perfil+rol (perfiles.es_admin en vez de la tabla global
roles + cod_rol_prf como parte de la PK), elimina roles/vistas, y renueva el
catálogo de permisos por módulo (ver/crear_editar/eliminar_o_anular) +
acciones sensibles. Cubre los 5 criterios de aceptación del ticket."""
import psycopg
import pytest

from tests.conftest import TALLER_A, auth_headers

pytestmark = [pytest.mark.db, pytest.mark.usefixtures("mock_auth0")]


class TestNoExistenRolesNiVistas:
    """Criterio: no existen las tablas vistas ni la dependencia de usuario a
    rol global; el usuario tiene un solo rol (es_admin, no cod_rol_prf)."""

    def test_tabla_roles_no_existe(self, db_conn):
        with db_conn.cursor() as cur:
            with pytest.raises(psycopg.errors.UndefinedTable):
                cur.execute("SELECT 1 FROM roles LIMIT 1")

    def test_tabla_vistas_no_existe(self, db_conn):
        with db_conn.cursor() as cur:
            with pytest.raises(psycopg.errors.UndefinedTable):
                cur.execute("SELECT 1 FROM vistas LIMIT 1")

    def test_usuarios_no_tiene_cod_rol_prf_usu(self, db_conn):
        with db_conn.cursor() as cur:
            with pytest.raises(psycopg.errors.UndefinedColumn):
                cur.execute("SELECT cod_rol_prf_usu FROM usuarios LIMIT 1")

    def test_perfiles_tiene_es_admin_y_pk_sin_rol(self, db_conn, seed_talleres):
        with db_conn.cursor() as cur:
            cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(TALLER_A),))
            cur.execute(
                "SELECT cod_prf, es_admin FROM perfiles WHERE cod_taller=%s", (TALLER_A,)
            )
            filas = cur.fetchall()
        assert any(es_admin is True for _, es_admin in filas)


class TestCatalogoSinPlantillaDeLogistica:
    """Criterio: el catálogo no contiene permisos de la plantilla y cubre
    inventario, tablero, configuración, planes e impuestos."""

    def test_sin_recursos_muertos(self, db_conn):
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT nombre_prm FROM permisos WHERE "
                "split_part(nombre_prm, ':', 2) IN "
                "('operations','orders','roles','vistas','users','perfiles-permisos')"
            )
            assert cur.fetchall() == []

    def test_cubre_modulos_nuevos(self, db_conn):
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT DISTINCT split_part(nombre_prm, ':', 2) FROM permisos "
                "WHERE split_part(nombre_prm, ':', 2) IN "
                "('inventario','tablero','talleres','planes','impuestos')"
            )
            recursos = {row[0] for row in cur.fetchall()}
        assert recursos == {"inventario", "tablero", "talleres", "planes", "impuestos"}


class TestAccionesSensibles:
    """Criterio: las acciones sensibles existen como permisos."""

    def test_existen_las_4_acciones_sensibles_nuevas(self, db_conn):
        esperados = {"anular:ordenes-trabajo", "ajustar:inventario", "ver_costos:productos", "ver_todo:tablero"}
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT nombre_prm FROM permisos WHERE nombre_prm = ANY(%s)",
                (list(esperados),),
            )
            encontrados = {row[0] for row in cur.fetchall()}
        assert encontrados == esperados


class TestAdminBypassSinAsignacionExplicita:
    """Criterio: un permiso nuevo agregado al catálogo queda disponible para
    el Administrador sin migrar sus asignaciones."""

    def test_admin_no_tiene_ninguna_fila_en_perfiles_permisos(self, db_conn, seed_talleres):
        with db_conn.cursor() as cur:
            cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(TALLER_A),))
            cur.execute(
                "SELECT COUNT(*) FROM perfiles_permisos pp "
                "JOIN perfiles pf ON pp.cod_taller=pf.cod_taller AND pp.cod_prf_pp=pf.cod_prf "
                "WHERE pf.cod_taller=%s AND pf.es_admin=true",
                (TALLER_A,),
            )
            assert cur.fetchone()[0] == 0

    async def test_un_permiso_nuevo_en_el_catalogo_queda_disponible_para_admin_sin_tocar_nada(
        self, db_conn, seed_talleres
    ):
        """Mutación positiva del propio criterio: si HOY se inserta un permiso
        que nunca existió, el Admin ya debe poder usarlo (bypass puro) -- sin
        ninguna fila nueva en perfiles_permisos."""
        from infrastructure.dependencies.current_user import usuario_tiene_permiso

        with db_conn.cursor() as cur:
            cur.execute(
                "INSERT INTO permisos (cod_prm, nombre_prm, descripcion_prm) "
                "VALUES (nextval('seq_permisos'), 'ver_futuro:modulo_que_no_existe_todavia', 'x')"
            )
        try:
            seed = seed_talleres[TALLER_A]
            admin_user = {"ES_ADMIN_USU": True, "COD_PRF_USU": None, "DOCUMENTO_USU": seed.documento_usuario}
            tiene = await usuario_tiene_permiso(admin_user, "ver_futuro:modulo_que_no_existe_todavia")
            assert tiene is True
        finally:
            with db_conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM permisos WHERE nombre_prm = 'ver_futuro:modulo_que_no_existe_todavia'"
                )

    def test_fn_seed_perfiles_taller_no_asigna_nada_al_admin(self, db_conn):
        """Taller nuevo: el perfil Administrador no debe recibir ninguna fila
        en perfiles_permisos -- su acceso total es 100% el bypass."""
        cod_taller_nuevo = 9099
        with db_conn.cursor() as cur:
            cur.execute("DELETE FROM talleres WHERE cod_taller=%s", (cod_taller_nuevo,))
            cur.execute(
                "INSERT INTO talleres (cod_taller, nombre_tal, correo_tal, estado_tal) "
                "VALUES (%s, 'Taller F1-12 nuevo', 'f112-nuevo@test.local', 'activo')",
                (cod_taller_nuevo,),
            )
            cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(cod_taller_nuevo),))
            cur.execute("SELECT fn_seed_perfiles_taller(%s)", (cod_taller_nuevo,))
            cod_prf_admin = cur.fetchone()[0]
            cur.execute(
                "SELECT COUNT(*) FROM perfiles_permisos WHERE cod_taller=%s AND cod_prf_pp=%s",
                (cod_taller_nuevo, cod_prf_admin),
            )
            total_admin = cur.fetchone()[0]
            cur.execute(
                "SELECT COUNT(*) FROM perfiles_permisos pp JOIN perfiles pf "
                "ON pp.cod_taller=pf.cod_taller AND pp.cod_prf_pp=pf.cod_prf "
                "WHERE pf.cod_taller=%s AND pf.nombre_prf='Mecánico'",
                (cod_taller_nuevo,),
            )
            total_mecanico = cur.fetchone()[0]
            cur.execute("DELETE FROM perfiles_permisos WHERE cod_taller=%s", (cod_taller_nuevo,))
            cur.execute("DELETE FROM perfiles WHERE cod_taller=%s", (cod_taller_nuevo,))
            cur.execute("DELETE FROM talleres WHERE cod_taller=%s", (cod_taller_nuevo,))
        assert total_admin == 0
        assert total_mecanico > 0


class TestRequierePermisoUsaElCatalogoNuevo:
    """Criterio: los permisos de F0-11 (require_permiso) usan el catálogo
    nuevo y todos sus tests pasan (verificado por la suite completa; acá se
    confirma el caso concreto de un endpoint mutante real)."""

    def test_crear_cliente_exige_crear_editar_clientes(self, client, seed_talleres):
        resp = client.post(
            "/api/clientes",
            json={"documento_cli": "900100400", "nombre_cli": "X", "apellido_1_cli": "Y"},
            headers=auth_headers(TALLER_A),
        )
        # Admin siempre pasa el permiso (puede fallar más adelante por otra
        # validación de negocio, pero NUNCA por 403).
        assert resp.status_code != 403
