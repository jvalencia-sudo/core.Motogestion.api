"""F1-12 regresión real: TallerServicio.registrar() seguía pasando el cod_rol
viejo (el entero 1) al nuevo crear_pre_registrado(..., es_admin: bool) después
de la migración a roles simplificados. psycopg rechaza el tipo al mandarlo a
Postgres (DatatypeMismatch: boolean vs smallint) y el registro de un taller
nuevo quedaba a medias: el taller ya commiteado, pero el usuario dueño nunca
se insertaba -- el dueño no podía ni reintentar (400 "ya existe un taller con
ese correo") ni iniciar sesión (403 "usuario no registrado"). Se detectó
registrando un taller de verdad contra la BD de desarrollo."""
import pytest

pytestmark = pytest.mark.db

CORREO_REGISTRO = "regresion-f112-registro@example.com"


def _borrar_taller_por_correo(db_conn, correo: str) -> None:
    """Busca por correo (no por el cod_taller de la respuesta): el bug real
    deja un taller creado SIN que el POST devuelva 201, así que una limpieza
    basada en resp.json() no encontraría nada que borrar."""
    with db_conn.cursor() as cur:
        cur.execute("SELECT cod_taller FROM talleres WHERE correo_tal = %s", (correo,))
        fila = cur.fetchone()
        if not fila:
            return
        cod_taller = fila[0]
        cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(cod_taller),))
        for tabla in ("perfiles_permisos", "usuarios", "perfiles", "marcas", "impuestos"):
            cur.execute(f"DELETE FROM {tabla} WHERE cod_taller = %s", (cod_taller,))
        cur.execute("DELETE FROM talleres WHERE cod_taller = %s", (cod_taller,))


def test_registrar_taller_crea_el_usuario_dueno_como_admin(client, db_conn):
    try:
        resp = client.post(
            "/api/talleres",
            json={
                "nombreTal": "Taller Regresion F112",
                "correo": CORREO_REGISTRO,
                "nombreDueno": "Dueno De Prueba",
            },
        )
        assert resp.status_code == 201
        cod_taller = resp.json()["codTaller"]

        with db_conn.cursor() as cur:
            cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(cod_taller),))
            cur.execute(
                "SELECT es_admin_usu FROM usuarios WHERE cod_taller = %s AND correo_usu = %s",
                (cod_taller, CORREO_REGISTRO),
            )
            fila = cur.fetchone()

        # El bug dejaba esto en None (el INSERT nunca llegó a correr) -- lo
        # correcto es exactamente un usuario, ya marcado es_admin_usu=true.
        assert fila is not None, (
            "El usuario dueño nunca se creó: el registro quedó a medias "
            "(mismo síntoma que el bug real: taller creado, login 403)."
        )
        assert fila[0] is True
    finally:
        _borrar_taller_por_correo(db_conn, CORREO_REGISTRO)
