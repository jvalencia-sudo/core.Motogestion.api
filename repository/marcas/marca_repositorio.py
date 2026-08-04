from typing import Dict, List, Optional
from repository.base_repository import BaseRepository


class MarcaRepositorio(BaseRepository):
    def __init__(self):
        super().__init__(
            schema="",
            table_name="marcas",
            primary_key="cod_mar",
            omit_key=True,
            sequence_name="seq_marcas"
        )

    async def existe_marca(self, nombre_mar: str, excluir_cod: Optional[int] = None) -> bool:
        """Verifica si existe una marca con ese nombre"""
        if excluir_cod:
            query = "SELECT COUNT(*) as count FROM marcas WHERE UPPER(nombre_mar) = UPPER(:1) AND cod_mar != :2"
            result = await self.get_one(query, (nombre_mar, excluir_cod))
        else:
            query = "SELECT COUNT(*) as count FROM marcas WHERE UPPER(nombre_mar) = UPPER(:1)"
            result = await self.get_one(query, (nombre_mar,))

        return result.get('COUNT', 0) > 0 if result else False

    async def obtener_marcas_con_resumen(self) -> List[Dict]:
        """Obtiene marcas con total de motos registradas (vw_marcas_resumen)"""
        query = "SELECT * FROM vw_marcas_resumen ORDER BY nombre_mar"
        return await self.execute(query, None)

    async def crear(self, nombre_mar: str) -> None:
        """Crea una marca en el taller actual (cod_taller por DEFAULT app.tenant_id)."""
        await self.execute_non_query(
            "INSERT INTO marcas (nombre_mar) VALUES (:1)", (nombre_mar,)
        )


