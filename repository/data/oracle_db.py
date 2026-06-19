import re
from typing import Optional, Tuple, Any, List, Dict, NoReturn

import pandas as pd

from config import settings
from repository.data.db_pool import get_pool

Params = Tuple[Any, ...]

# Detecta binds estilo Oracle (:1, :2, ...)
_BIND_RE = re.compile(r":\d+")


def _translate(query: str) -> str:
    """Traduce binds estilo Oracle (:1, :2) al estilo de psycopg (%s).

    Solo actua si la consulta usa binds Oracle. En ese caso, primero escapa
    los '%' literales (para que psycopg no los interprete como placeholders)
    y luego reemplaza :N -> %s. Las consultas que ya usan %s se dejan intactas.
    """
    if _BIND_RE.search(query):
        query = query.replace("%", "%%")
        query = _BIND_RE.sub("%s", query)
    return query


def _columns_upper(description) -> List[str]:
    """Nombres de columna en MAYUSCULAS para replicar el comportamiento de
    Oracle (sobre el que se escribieron los modelos/servicios del proyecto)."""
    return [col[0].upper() for col in description]


class OracleDb:
    """Wrapper de acceso a datos. Conserva el nombre y la API original para no
    tocar los repositorios; internamente usa psycopg3 sobre PostgreSQL."""

    def __init__(self):
        self.config = settings.db_config

    async def get_as_data_frame(self, query: str, params: Optional[Params] = None) -> pd.DataFrame:
        """Ejecuta una consulta y devuelve un DataFrame de pandas"""
        pool = get_pool()
        async with pool.connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(_translate(query), params)
                columns = _columns_upper(cursor.description)
                rows = await cursor.fetchall()
                return pd.DataFrame(rows, columns=columns)

    async def execute(self, query: str, params: Optional[Params] = None) -> List[Dict]:
        """Ejecuta una consulta SELECT y devuelve una lista de diccionarios"""
        pool = get_pool()
        async with pool.connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(_translate(query), params)
                columns = _columns_upper(cursor.description)
                rows = await cursor.fetchall()
                return [dict(zip(columns, row)) for row in rows]

    async def execute_many_non_query(self, query: str, params: List[Params]) -> NoReturn:
        """Ejecuta múltiples consultas (INSERT, UPDATE, DELETE)"""
        pool = get_pool()
        async with pool.connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.executemany(_translate(query), params)
                await conn.commit()

    async def insert(self, query: str, params: Params, primary_key: str = None) -> Dict:
        """Ejecuta un INSERT y, si se indica primary_key, devuelve el ID generado
        usando RETURNING (lo aporta el DEFAULT nextval o un trigger)."""
        pool = get_pool()
        try:
            async with pool.connection() as conn:
                async with conn.cursor() as cursor:
                    if primary_key:
                        returning_query = f"{_translate(query)} RETURNING {primary_key}"
                        await cursor.execute(returning_query, params)
                        row = await cursor.fetchone()
                        await conn.commit()
                        generated_id = row[0] if row else None
                        return {primary_key: generated_id, "affected_rows": cursor.rowcount}

                    await cursor.execute(_translate(query), params)
                    await conn.commit()
                    return {"affected_rows": cursor.rowcount}
        except Exception as e:
            print(f"=== ERROR en INSERT: {e} ===")
            print(f"=== Tipo de error: {type(e).__name__} ===")
            raise e

    async def execute_non_query(self, query: str, params: Optional[Params] = None) -> NoReturn:
        """Ejecuta una consulta que no devuelve resultados (INSERT, UPDATE, DELETE)"""
        pool = get_pool()
        try:
            async with pool.connection() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(_translate(query), params)
                    await conn.commit()
        except Exception as e:
            error_msg = str(e).lower()
            print(f"=== ERROR en execute_non_query: {e} ===")
            print(f"=== Tipo de error: {type(e).__name__} ===")

            # Detectar errores de integridad referencial (FK) en PostgreSQL
            # (SQLSTATE 23503 = foreign_key_violation)
            if (
                "foreign key" in error_msg
                or "23503" in error_msg
                or "viola" in error_msg and "llave foránea" in error_msg
            ):
                raise Exception("ERROR_INTEGRIDAD_REFERENCIAL")

            raise e

    async def execute_values(self, query: str, params: List[Params]):
        """Ejecuta múltiples valores"""
        pool = get_pool()
        async with pool.connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.executemany(_translate(query), params)
                await conn.commit()

    async def get_first(self, query: str, params: Optional[Params] = None) -> Optional[Dict]:
        """Ejecuta una consulta y devuelve el primer resultado como diccionario"""
        pool = get_pool()
        async with pool.connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(_translate(query), params)
                row = await cursor.fetchone()
                if row:
                    columns = _columns_upper(cursor.description)
                    return dict(zip(columns, row))
                return None
