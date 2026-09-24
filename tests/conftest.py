"""Fixtures compartidas por los tests de integración (@pytest.mark.db).

Fuerza DB_NAME a una BD DEDICADA (motogestion_test por defecto, override con
TEST_DB_NAME) antes de que nada importe `config`/`main` — así tanto el pool async de
la app (usado por TestClient) como la conexión síncrona de seed de este archivo
apuntan a la misma BD, y nunca a la de desarrollo/producción del .env. El guardrail
de abajo lo confirma en runtime: si algún día algo rompe este override, la fixture
falla ruidosamente en vez de sembrar/borrar datos en la BD equivocada.
"""
import os

os.environ["DB_NAME"] = os.environ.get("TEST_DB_NAME", "motogestion_test")

from typing import NamedTuple  # noqa: E402
from unittest.mock import patch  # noqa: E402

import psycopg  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from config import settings  # noqa: E402
from domain.models.auth.user_model import UserPermissionsModel  # noqa: E402
from main import app  # noqa: E402

TALLER_A = 9001
TALLER_B = 9002

_SUB_POR_TALLER = {TALLER_A: "test|taller-a", TALLER_B: "test|taller-b"}
_TOKEN_POR_TALLER = {TALLER_A: "test-token-taller-a", TALLER_B: "test-token-taller-b"}
_SUB_POR_TOKEN = {token: _SUB_POR_TALLER[t] for t, token in _TOKEN_POR_TALLER.items()}


def auth_headers(taller: int) -> dict:
    """Headers de Authorization para actuar como el usuario semilla de ese taller."""
    return {"Authorization": f"Bearer {_TOKEN_POR_TALLER[taller]}"}


class TallerSeed(NamedTuple):
    cod_taller: int
    documento_usuario: str
    documento_cliente: str
    placa_moto: str
    cod_producto: int
    consecutivo_ot: int
    cod_reclamo: int
    cod_movimiento: int
    cod_marca: int
    cod_pago: int


def _dsn() -> str:
    c = settings.db_config
    # connect_timeout corto: sin esto, psycopg.connect() puede colgarse en vez de
    # fallar cuando el host no responde (en vez de rechazar la conexión al toque),
    # y el pytest.fail/skip de abajo nunca se alcanza — el job simplemente cuelga
    # hasta el timeout del runner.
    return (
        f"host={c.host} port={c.port} dbname={c.dbname} user={c.user} "
        f"password={c.password} connect_timeout=5"
    )


def conectar_o_fallar(dsn: str, **kwargs) -> psycopg.Connection:
    """Conecta o, si Postgres no está disponible: en CI es un pytest.fail (un test de
    seguridad que se salta silenciosamente es exactamente el tipo de falla silenciosa
    que F0-02 busca evitar — GitHub Actions define CI=true por su cuenta); en local
    es un pytest.skip, para no bloquear a quien no tiene `docker compose up -d`
    corriendo."""
    try:
        return psycopg.connect(dsn, **kwargs)
    except psycopg.OperationalError:
        c = settings.db_config
        mensaje = f"Postgres no disponible en {c.host}:{c.port}/{c.dbname}"
        if os.getenv("CI") == "true":
            pytest.fail(f"{mensaje} — en CI esto es un error, no un salto silencioso.")
        pytest.skip(f"{mensaje} (corre `docker compose up -d`)")


@pytest.fixture(scope="session")
def db_conn():
    conn = conectar_o_fallar(_dsn(), autocommit=True)

    with conn.cursor() as cur:
        cur.execute("SELECT current_database()")
        nombre = cur.fetchone()[0]
    if not nombre.endswith("_test"):
        conn.close()
        raise RuntimeError(
            f"La BD de test resolvió a '{nombre}', que no termina en '_test'. Los "
            "tests de este archivo SIEMBRAN Y BORRAN datos: nunca deben correr contra "
            "la BD de desarrollo o producción. Revisa TEST_DB_NAME / tu .env."
        )

    yield conn
    conn.close()


@pytest.fixture
def mock_auth0():
    """Todas las dependencias de auth activas (resolve_tenant, get_current_usuario,
    require_admin, require_active_subscription) llaman Auth0Provider().verify(token)
    de forma independiente e inline (no hay un único Depends() que las cubra a todas
    con app.dependency_overrides) — así que se parchea ese método de clase, que todas
    comparten. El resto de la cadena (IdentidadRepositorio, UserRepository,
    _apply_tenant, TallerRepositorio) corre de verdad contra la BD de test.

    NO es autouse: solo lo piden explícitamente (vía pytestmark/usefixtures) los
    archivos que hacen requests HTTP simuladas. Si fuera global, parchearía
    Auth0Provider.verify incluso en tests que sí quieren probar ese método real (hoy
    no hay ninguno, pero silenciaría un fallo real el día que se escriba uno)."""

    async def _verify(self, token: str) -> UserPermissionsModel:
        sub = _SUB_POR_TOKEN.get(token)
        if sub is None:
            raise ValueError(f"Token de test desconocido: {token!r}")
        return UserPermissionsModel(user_id=sub, permissions=["*"])

    with patch(
        "infrastructure.providers.auth.auth0_provider.Auth0Provider.verify",
        new=_verify,
    ):
        yield


@pytest.fixture(scope="module")
def client():
    # El lifespan real de la app abre el pool async en el loop propio de TestClient
    # (evita el choque de event loop de crear el pool en un fixture de pytest-asyncio
    # aparte) y de paso ejercita el startup check de db_pool.py.
    with TestClient(app) as c:
        yield c


def _seed_taller(cur, cod_taller: int) -> TallerSeed:
    sub = _SUB_POR_TALLER[cod_taller]
    documento_usuario = f"900{cod_taller}01"
    documento_cliente = f"900{cod_taller}02"
    placa_moto = f"T{cod_taller % 1000:03d}AA"  # exactamente 6 chars (VARCHAR(6))

    cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(cod_taller),))

    # tarifa_hora_pred = cod_taller (valor "marcado", distinto entre A y B) para que
    # un test de /talleres/config pueda confirmar que cada uno ve la suya, no la
    # ajena — talleres no tiene RLS (ver rls_policy.py), la única barrera es que
    # require_admin resuelva bien el taller del token.
    cur.execute(
        "INSERT INTO talleres (cod_taller, nombre_tal, correo_tal, estado_tal, tarifa_hora_pred) "
        "VALUES (%s, %s, %s, 'activo', %s) ON CONFLICT (cod_taller) DO NOTHING",
        (cod_taller, f"Taller de prueba {cod_taller}", f"taller{cod_taller}@test.local", cod_taller),
    )

    cur.execute(
        "INSERT INTO perfiles (cod_taller, cod_rol_prf, cod_est_prf, nombre_prf) "
        "VALUES (%s, 1, 1, 'Admin de prueba') RETURNING cod_prf",
        (cod_taller,),
    )
    cod_prf = cur.fetchone()[0]

    cur.execute(
        "INSERT INTO usuarios (cod_taller, documento_usu, nombre_usu, apellido_1_usu, "
        "correo_usu, contrasena_usu, cod_tipo_usu, cod_est_usu, sub_id_usu, "
        "cod_prf_usu, cod_rol_prf_usu) "
        "VALUES (%s, %s, 'Usuario', 'De Prueba', %s, 'test', 1, 1, %s, %s, 1)",
        (cod_taller, documento_usuario, f"user{cod_taller}@test.local", sub, cod_prf),
    )

    cur.execute(
        "INSERT INTO marcas (cod_taller, nombre_mar) VALUES (%s, 'Marca de prueba') "
        "RETURNING cod_mar",
        (cod_taller,),
    )
    cod_marca = cur.fetchone()[0]

    cur.execute(
        "INSERT INTO clientes (cod_taller, documento_cli, nombre_cli, apellido_1_cli, "
        "telefono_cli, correo_cli) VALUES (%s, %s, 'Cliente', 'De Prueba', '3000000000', %s)",
        (cod_taller, documento_cliente, f"cliente{cod_taller}@test.local"),
    )

    cur.execute(
        "INSERT INTO motos (cod_taller, placa_mot, modelo_mot, color_mot, "
        "cilindraje_mot, documento_cli_mot, cod_marca_mot) "
        "VALUES (%s, %s, 2024, 'Negro', 150, %s, %s)",
        (cod_taller, placa_moto, documento_cliente, cod_marca),
    )

    cur.execute(
        "INSERT INTO productos (cod_taller, nombre_pro, stock_pro, stock_pro_min, "
        "cod_est_pro, precio_pro, tipo_pro) "
        "VALUES (%s, 'Producto de prueba', 10, 2, 1, 50000, 'BIEN') RETURNING cod_pro",
        (cod_taller,),
    )
    cod_producto = cur.fetchone()[0]

    # Único por taller (no colisiona entre A y B) para que un GET cross-tenant por
    # este ID sea inequívocamente "no encontrado" y no "vio el otro por coincidencia".
    consecutivo_ot = cod_taller - 9000
    cur.execute(
        "INSERT INTO ordenes_trabajo (cod_taller, consecutivo_ot, fecha_elaboracion_ot, "
        "kilometraje_ingreso_ot, placa_mot_ot, documento_usu_rp_ot, documento_usu_mc_ot, "
        "cod_ot_est_ot) VALUES (%s, %s, CURRENT_DATE, 15000, %s, %s, %s, 1)",
        (cod_taller, consecutivo_ot, placa_moto, documento_usuario, documento_usuario),
    )

    cur.execute(
        "INSERT INTO detalle_orden_trabajo (cod_taller, consecutivo_ot_deto, "
        "cod_pro_deto, fecha_confirmacion_deto, valor_unitario_deto, cantidad_deto, "
        "documento_usu_deto) VALUES (%s, %s, %s, CURRENT_DATE, 50000, 1, %s)",
        (cod_taller, consecutivo_ot, cod_producto, documento_usuario),
    )

    cur.execute(
        "INSERT INTO reclamos (cod_taller, descripcion_rec, consecutivo_ot_rec) "
        "VALUES (%s, 'Reclamo de prueba', %s) RETURNING cod_rec",
        (cod_taller, consecutivo_ot),
    )
    cod_reclamo = cur.fetchone()[0]

    cur.execute(
        "INSERT INTO movimientos_inventario (cod_taller, cod_pro_mov, tipo_mov, "
        "cantidad_mov, stock_ant_mov, stock_nue_mov, motivo_mov) "
        "VALUES (%s, %s, 'ENTRADA', 10, 0, 10, 'seed de test') RETURNING cod_mov",
        (cod_taller, cod_producto),
    )
    cod_movimiento = cur.fetchone()[0]

    # pagos no tiene RLS (billing de plataforma, ver rls_policy.py): el único
    # aislamiento es el filtro aplicativo por cod_taller en PagoRepositorio. La
    # respuesta del endpoint es un dict crudo (sin el contrato camelCase), con
    # columnas en MAYÚSCULAS — no incluye "referencia", así que el test usa cod_pago.
    cur.execute(
        "INSERT INTO pagos (cod_taller, nombre_plan, monto, referencia, estado) "
        "VALUES (%s, 'Profesional', 49000, %s, 'APPROVED') RETURNING cod_pago",
        (cod_taller, f"TEST-{cod_taller}"),
    )
    cod_pago = cur.fetchone()[0]

    return TallerSeed(
        cod_taller=cod_taller,
        documento_usuario=documento_usuario,
        documento_cliente=documento_cliente,
        placa_moto=placa_moto,
        cod_producto=cod_producto,
        consecutivo_ot=consecutivo_ot,
        cod_reclamo=cod_reclamo,
        cod_movimiento=cod_movimiento,
        cod_marca=cod_marca,
        cod_pago=cod_pago,
    )


def _borrar_taller(cur, cod_taller: int) -> None:
    # pagos no tiene RLS: se borra sin depender de app.tenant_id.
    cur.execute("DELETE FROM pagos WHERE cod_taller = %s", (cod_taller,))
    cur.execute("SELECT set_config('app.tenant_id', %s, false)", (str(cod_taller),))
    # reclamos y detalle_orden_trabajo van ANTES que movimientos_inventario: borrar
    # detalle_orden_trabajo dispara tg_revertir_stock (fn_revertir_stock_detalle),
    # que INSERTA un movimiento de reversa nuevo — si movimientos_inventario se
    # borrara antes, ese movimiento nuevo sobrevive y bloquea el DELETE de productos.
    for tabla in (
        "reclamos",
        "detalle_orden_trabajo",
        "ordenes_trabajo",
        "movimientos_inventario",
        "productos",
        "motos",
        "clientes",
        "marcas",
        "usuarios",
        "perfiles",
    ):
        cur.execute(f"DELETE FROM {tabla} WHERE cod_taller = %s", (cod_taller,))
    # talleres no tiene RLS (ver infrastructure/utils/rls_policy.py): se borra aparte,
    # de último, una vez ya no quedan filas hijas que lo referencien.
    cur.execute("DELETE FROM talleres WHERE cod_taller = %s", (cod_taller,))


@pytest.fixture(scope="module")
def seed_talleres(db_conn):
    """Siembra dos talleres de prueba (A=9001, B=9002) con un registro por módulo
    cada uno, y los borra al terminar. IDs reservados fuera del rango de cualquier
    dato real (las secuencias de la app empiezan en 1)."""
    with db_conn.cursor() as cur:
        _borrar_taller(cur, TALLER_A)
        _borrar_taller(cur, TALLER_B)
        seed_a = _seed_taller(cur, TALLER_A)
        seed_b = _seed_taller(cur, TALLER_B)

    yield {TALLER_A: seed_a, TALLER_B: seed_b}

    with db_conn.cursor() as cur:
        _borrar_taller(cur, TALLER_A)
        _borrar_taller(cur, TALLER_B)
