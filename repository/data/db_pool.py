# db_pool.py - Pool de conexiones async para PostgreSQL (psycopg3)
import asyncio
import logging

from psycopg_pool import AsyncConnectionPool

from config import settings

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

pool: AsyncConnectionPool | None = None


def _build_conninfo() -> str:
    """Construye el string de conexion (DSN) de PostgreSQL desde settings."""
    c = settings.db_config
    return (
        f"host={c.host} port={c.port} dbname={c.dbname} "
        f"user={c.user} password={c.password}"
    )


async def _verificar_rol_no_privilegiado(cursor) -> None:
    """El RLS (FORCE ROW LEVEL SECURITY) solo aísla datos si el rol de la app no es
    superusuario ni tiene BYPASSRLS: cualquiera de los dos anula el RLS por completo
    y de forma silenciosa. Se verifica en cada arranque para que un despliegue con el
    rol equivocado falle ruidosamente en vez de exponer datos entre talleres."""
    await cursor.execute(
        "SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user"
    )
    row = await cursor.fetchone()
    rolsuper, rolbypassrls = row
    if rolsuper or rolbypassrls:
        raise RuntimeError(
            "El rol de BD configurado anula el RLS (rolsuper="
            f"{rolsuper}, rolbypassrls={rolbypassrls}). Usa un rol NOSUPERUSER "
            "sin BYPASSRLS para que el aislamiento entre talleres funcione."
        )


async def init_pool():
    """Inicializa el pool de conexiones async de PostgreSQL."""
    global pool

    try:
        c = settings.db_config
        logger.info(f"Inicializando pool para: {c.host}:{c.port}/{c.dbname}")

        # Crear el pool sin abrirlo en el constructor (recomendado en psycopg_pool)
        pool = AsyncConnectionPool(
            conninfo=_build_conninfo(),
            min_size=1,
            max_size=5,
            open=False,
        )
        await pool.open(wait=True)

        # Test simple del pool
        logger.info("Probando pool recién creado...")
        async with pool.connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT 1")
                await cursor.fetchone()
                await _verificar_rol_no_privilegiado(cursor)
        logger.info("✅ Test del pool exitoso")

        logger.info("✅ Pool de PostgreSQL inicializado correctamente")
        return pool

    except Exception as e:
        logger.error(f"❌ Error inicializando pool de PostgreSQL: {e}")
        raise Exception(f"Error de base de datos PostgreSQL: {e}")


async def close_pool():
    """Cierra el pool de conexiones"""
    global pool
    if pool:
        try:
            await pool.close()
            pool = None
            logger.info("🛑 Pool de PostgreSQL cerrado correctamente")
        except Exception as e:
            logger.error(f"❌ Error cerrando pool: {e}")


def get_pool() -> AsyncConnectionPool:
    """Obtiene la instancia del pool con validación"""
    global pool
    if pool is None:
        raise RuntimeError("Pool no inicializado")
    return pool


# Función de diagnóstico independiente
async def test_db_connection():
    """Test de diagnóstico independiente"""
    c = settings.db_config
    try:
        logger.info("🔍 Iniciando test de diagnóstico...")
        logger.info(f"Host: {c.host}  Puerto: {c.port}  DB: {c.dbname}  Usuario: {c.user}")
        async with await __import__("psycopg").AsyncConnection.connect(_build_conninfo()) as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT 'Hello PostgreSQL' AS mensaje, now() AS fecha")
                result = await cursor.fetchone()
                logger.info(f"✅ Query exitosa: {result}")
        logger.info("✅ Conexión cerrada correctamente")
        return True
    except Exception as e:
        logger.error(f"❌ Error en test: {e}  Tipo: {type(e).__name__}")
        return False


# Para ejecutar el diagnóstico independientemente
if __name__ == "__main__":
    asyncio.run(test_db_connection())
