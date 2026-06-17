from typing import Dict, List, Optional
from pydantic import BaseModel
from repository.base_repository import BaseRepository
from repository.data.db_pool import get_pool


class ProductoRepositorio(BaseRepository):
    def __init__(self):
        super().__init__(
            schema="",
            table_name="productos",
            primary_key="cod_pro",
            omit_key=True,
            sequence_name="seq_productos"
        )

    async def obtener_producto_con_impuestos(self, cod_pro: int) -> Optional[Dict]:
        """Obtiene un producto con sus impuestos asociados usando vista"""
        query = "SELECT * FROM vw_productos WHERE cod_pro = :1"
        return await self.get_one(query, (cod_pro,))

    async def obtener_todos_con_impuestos(self) -> List[Dict]:
        """Obtiene todos los productos con sus impuestos usando vista"""
        query = "SELECT * FROM vw_productos ORDER BY cod_pro"
        return await self.execute(query, None)

    async def obtener_activos(self) -> List[Dict]:
        """Obtiene solo los productos activos usando vista"""
        query = "SELECT * FROM vw_productos_activos ORDER BY nombre_pro"
        return await self.execute(query, None)

    async def desactivar_producto(self, cod_pro: int) -> None:
        """Desactiva un producto (soft delete)"""
        query = "UPDATE productos SET cod_est_pro = 2 WHERE cod_pro = :1"
        await self.execute_non_query(query, (cod_pro,))

    async def activar_producto(self, cod_pro: int) -> None:
        """Activa un producto"""
        query = "UPDATE productos SET cod_est_pro = 1 WHERE cod_pro = :1"
        await self.execute_non_query(query, (cod_pro,))

    async def existe_producto(self, nombre: str, excluir_cod: Optional[int] = None) -> bool:
        """Verifica si existe un producto con el mismo nombre"""
        if excluir_cod:
            query = "SELECT COUNT(*) as count FROM productos WHERE UPPER(nombre_pro) = UPPER(:1) AND cod_pro != :2"
            result = await self.get_one(query, (nombre, excluir_cod))
        else:
            query = "SELECT COUNT(*) as count FROM productos WHERE UPPER(nombre_pro) = UPPER(:1)"
            result = await self.get_one(query, (nombre,))

        return result.get('COUNT', 0) > 0 if result else False

    async def actualizar_stock(self, cod_pro: int, nuevo_stock: int) -> None:
        """Actualiza el stock de un producto"""
        query = "UPDATE productos SET stock_pro = :1 WHERE cod_pro = :2"
        await self.execute_non_query(query, (nuevo_stock, cod_pro))
