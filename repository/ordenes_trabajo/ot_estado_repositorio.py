from typing import List, Dict
from repository.base_repository import BaseRepository


class OtEstadoRepositorio(BaseRepository):
    def __init__(self):
        super().__init__(
            schema="",
            table_name="ot_estados",
            primary_key="cod_ot_est",
            omit_key=False
        )

    async def obtener_todos_estados(self) -> List[Dict]:
        """Obtiene todos los estados de ordenes de trabajo"""
        query = """
            SELECT cod_ot_est, nombre_ot_est
            FROM ot_estados
            ORDER BY cod_ot_est
        """
        return await self.execute(query, None)
