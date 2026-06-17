from typing import Optional, Tuple, Any, List, Dict, NoReturn
import pandas as pd
import asyncio
from config import settings
from repository.data.db_pool import get_pool

Params = Tuple[Any]


class OracleDb:
    def __init__(self):
        self.config = settings.db_config

    async def get_as_data_frame(self, query: str, params: Optional[Params] = None) -> pd.DataFrame:
        """Ejecuta una consulta y devuelve un DataFrame de pandas"""
        pool = get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(query, params)
                columns = [col[0] for col in cursor.description]
                rows = await cursor.fetchall()
                return pd.DataFrame(rows, columns=columns)

    async def execute(self, query: str, params: Optional[Params] = None) -> List[Dict]:
        """Ejecuta una consulta SELECT y devuelve una lista de diccionarios"""
        pool = get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(query, params)
                columns = [col[0] for col in cursor.description]
                rows = await cursor.fetchall()
                return [dict(zip(columns, row)) for row in rows]

    async def execute_many_non_query(
        self, query: str, params: List[Params]
    ) -> NoReturn:
        """
        Ejecuta múltiples consultas (INSERT, UPDATE, DELETE)
        """
        pool = get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.executemany(query, params)
                await conn.commit()

    async def insert(self, query: str, params: Params, primary_key: str = None) -> Dict:
        """
        Ejecuta una consulta INSERT con timeout y opcionalmente retorna el ID generado
        Si primary_key se proporciona, usa RETURNING para obtener el ID generado por IDENTITY
        """
        print(f"=== DEBUG INSERT OracleDb ===")
        print(f"Query: {query}")
        print(f"Params: {params}")
        print(f"Primary key: {primary_key}")

        pool = get_pool()
        print("=== Adquiriendo conexión async del pool ===")

        try:
            # Timeout de 10 segundos para todo el proceso
            async with asyncio.timeout(10):
                async with pool.acquire() as conn:
                    print("=== Conexión adquirida ===")

                    # Desactivar autocommit para poder usar RETURNING
                    conn.autocommit = False
                    print("=== Autocommit desactivado (para RETURNING) ===")

                    async with conn.cursor() as cursor:
                        print("=== Cursor creado ===")

                        # Si se especifica primary_key, agregar RETURNING para obtener el ID
                        if primary_key:
                            # Variable de salida para el ID generado
                            out_id = cursor.var(int)

                            # Modificar query para incluir RETURNING
                            returning_query = f"{query} RETURNING {primary_key} INTO :out_id"
                            print(f"=== Query con RETURNING: {returning_query} ===")

                            # Ejecutar con parámetros + variable de salida
                            await cursor.execute(returning_query, tuple(params) + (out_id,))
                            await conn.commit()

                            # Obtener el ID generado
                            generated_id = out_id.getvalue()[0]
                            print(f"=== INSERT exitoso, ID generado: {generated_id} ===")

                            return {primary_key: generated_id, "affected_rows": cursor.rowcount}
                        else:
                            # Sin RETURNING, comportamiento anterior
                            print("=== Ejecutando INSERT (sin RETURNING) ===")
                            await cursor.execute(query, params)
                            await conn.commit()

                            print(f"=== INSERT exitoso, rows affected: {cursor.rowcount} ===")
                            return {"affected_rows": cursor.rowcount}

        except asyncio.TimeoutError:
            print("=== TIMEOUT: El INSERT tardó más de 10 segundos ===")
            raise Exception("INSERT timeout después de 10 segundos")
        except Exception as e:
            print(f"=== ERROR en INSERT: {e} ===")
            print(f"=== Tipo de error: {type(e).__name__} ===")
            raise e

    async def execute_non_query(
        self, query: str, params: Optional[Params] = None
    ) -> NoReturn:
        """
        Ejecuta una consulta que no devuelve resultados (INSERT, UPDATE, DELETE)
        """
        pool = get_pool()
        try:
            async with pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(query, params)
                    await conn.commit()
        except Exception as e:
            error_msg = str(e).lower()
            print(f"=== ERROR en execute_non_query: {e} ===")
            print(f"=== Tipo de error: {type(e).__name__} ===")

            # Detectar errores de integridad referencial
            if "foreign key" in error_msg or "constraint" in error_msg or "ora-02291" in error_msg:
                raise Exception("ERROR_INTEGRIDAD_REFERENCIAL")

            raise e

    async def execute_values(self, query: str, params: List[Params]):
        """Ejecuta múltiples valores"""
        pool = get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.executemany(query, params)
                await conn.commit()

    async def get_first(self, query: str, params: Optional[Params] = None) -> Optional[Dict]:
        """Ejecuta una consulta y devuelve el primer resultado como diccionario"""
        pool = get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(query, params)
                row = await cursor.fetchone()
                if row:
                    columns = [col[0] for col in cursor.description]
                    return dict(zip(columns, row))
                return None

    async def call_procedure(self, procedure_name: str, params: List[Any]) -> Any:
        """Llama a un procedimiento almacenado de Oracle"""
        pool = get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                result = await cursor.callproc(procedure_name, params)
                await conn.commit()
                return result

    async def call_function(self, function_name: str, return_type, params: List[Any]) -> Any:
        """Llama a una función de Oracle"""
        pool = get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                result = await cursor.callfunc(function_name, return_type, params)
                await conn.commit()
                return result
