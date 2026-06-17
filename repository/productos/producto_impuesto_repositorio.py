from typing import Dict, List, Optional
from pydantic import BaseModel
from repository.base_repository import BaseRepository
from repository.data.db_pool import get_pool


class ProductoImpuestoRepositorio(BaseRepository):
    def __init__(self):
        super().__init__(
            schema="",
            table_name="productos_impuestos",
            primary_key="cod_pro_imp",
            omit_key=True,
            sequence_name="seq_productos_impuestos"
        )

    async def obtener_impuestos_por_producto(self, cod_pro: int) -> List[Dict]:
        """Obtiene todos los impuestos asociados a un producto usando vista"""
        query = "SELECT * FROM vw_productos_impuestos WHERE cod_pro_pro_imp = :1"
        return await self.execute(query, (cod_pro,))

    async def eliminar_impuestos_producto(self, cod_pro: int) -> None:
        """Elimina todos los impuestos asociados a un producto"""
        query = "DELETE FROM productos_impuestos WHERE cod_pro_pro_imp = :1"
        await self.execute_non_query(query, (cod_pro,))

    async def existe_impuesto_en_producto(self, cod_pro: int, cod_imp: int) -> bool:
        """Verifica si un impuesto ya está asociado a un producto"""
        query = """
        SELECT COUNT(*) as count
        FROM productos_impuestos
        WHERE cod_pro_pro_imp = :1 AND cod_imp_pro_imp = :2
        """
        result = await self.get_one(query, (cod_pro, cod_imp))
        return result.get('COUNT', 0) > 0 if result else False

    async def actualizar_porcentaje_impuesto(self, cod_pro: int, cod_imp: int, porcentaje: float) -> None:
        """Actualiza el porcentaje de un impuesto en un producto"""
        query = """
        UPDATE productos_impuestos
        SET porcentaje_pro_imp = :1
        WHERE cod_pro_pro_imp = :2 AND cod_imp_pro_imp = :3
        """
        await self.execute_non_query(query, (porcentaje, cod_pro, cod_imp))
