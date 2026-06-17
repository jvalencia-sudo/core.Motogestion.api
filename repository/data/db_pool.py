# db_pool.py - Versión simplificada
import oracledb
import asyncio
from config import settings
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

pool = None


async def init_pool():
    """Inicializa el pool de conexiones async de Oracle - versión simplificada"""
    global pool

    try:
        config = settings.db_config

        logger.info(f"Inicializando pool para: {config.host}:{config.port}/{config.service_name}")

        # Crear DSN
        dsn = oracledb.makedsn(
            host=config.host,
            port=config.port,
            service_name=config.service_name
        )

        # Crear pool asíncrono con configuración mínima
        pool = oracledb.create_pool_async(
            user=config.user,
            password=config.password,
            dsn=dsn,
            min=1,
            max=5,
            increment=1
        )

        # Test simple del pool
        logger.info("Probando pool recién creado...")
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT 'Pool funcionando' FROM dual")
                result = await cursor.fetchone()
                logger.info(f"✅ Test del pool exitoso: {result[0]}")

        logger.info("✅ Pool de Oracle inicializado correctamente")
        return pool

    except oracledb.DatabaseError as e:
        logger.error(f"❌ Error de Oracle Database: {e}")
        raise Exception(f"Error de base de datos Oracle: {e}")
    except oracledb.Error as e:
        logger.error(f"❌ Error de Oracle: {e}")
        raise Exception(f"Error de Oracle: {e}")
    except Exception as e:
        logger.error(f"❌ Error inesperado: {e}")
        raise Exception(f"Error inicializando pool: {e}")


async def close_pool():
    """Cierra el pool de conexiones"""
    global pool
    if pool:
        try:
            await pool.close()
            pool = None
            logger.info("🛑 Pool de Oracle cerrado correctamente")
        except Exception as e:
            logger.error(f"❌ Error cerrando pool: {e}")


def get_pool():
    """Obtiene la instancia del pool con validación"""
    global pool
    if pool is None:
        raise RuntimeError("Pool no inicializado")
    return pool


# Función de diagnóstico independiente
async def test_oracle_connection():
    """Test de diagnóstico independiente"""
    config = settings.db_config

    try:
        logger.info("🔍 Iniciando test de diagnóstico...")
        logger.info(f"Host: {config.host}")
        logger.info(f"Puerto: {config.port}")
        logger.info(f"Service Name: {config.service_name}")
        logger.info(f"Usuario: {config.user}")

        # Crear DSN
        dsn = oracledb.makedsn(
            host=config.host,
            port=config.port,
            service_name=config.service_name
        )

        logger.info(f"DSN construido: {dsn}")

        # Test de conexión directa
        logger.info("Probando conexión directa...")
        conn = await oracledb.connect_async(
            user=config.user,
            password=config.password,
            dsn=dsn
        )

        logger.info("✅ Conexión establecida")

        # Test de query
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT 'Hello Oracle' as mensaje, SYSDATE as fecha FROM dual")
            result = await cursor.fetchone()
            logger.info(f"✅ Query exitosa: {result}")

        await conn.close()
        logger.info("✅ Conexión cerrada correctamente")

        return True

    except Exception as e:
        logger.error(f"❌ Error en test: {e}")
        logger.error(f"Tipo: {type(e).__name__}")
        return False


# Para ejecutar el diagnóstico independientemente
if __name__ == "__main__":
    asyncio.run(test_oracle_connection())
