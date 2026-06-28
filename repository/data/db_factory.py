import psycopg

from config import settings


class DbFactory:
    """Crea conexiones async puntuales a PostgreSQL (psycopg3).

    Nota: el acceso a datos del proyecto va por el pool (ver db_pool.py /
    database.py). Esta fabrica se conserva por compatibilidad.
    """

    def __init__(self):
        self.config = settings.db_config

    def _conninfo(self) -> str:
        c = self.config
        return (
            f"host={c.host} port={c.port} dbname={c.dbname} "
            f"user={c.user} password={c.password}"
        )

    async def connect(self) -> psycopg.AsyncConnection:
        return await psycopg.AsyncConnection.connect(self._conninfo())
