from typing import Dict, List, Optional
from repository.base_repository import BaseRepository


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
        await self.soft_delete(cod_pro, 'cod_est_pro', 2)

    async def activar_producto(self, cod_pro: int) -> None:
        """Activa un producto"""
        await self.update_field(cod_pro, 'cod_est_pro', 1)

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
        await self.update_field(cod_pro, 'stock_pro', nuevo_stock)

    async def obtener_stock(self, cod_pro: int) -> Optional[int]:
        """Devuelve el stock actual de un producto (None si no existe)."""
        row = await self.get_one(
            "SELECT stock_pro FROM productos WHERE cod_pro = :1", (cod_pro,)
        )
        return row.get("STOCK_PRO") if row else None

    @staticmethod
    def statement_actualizar_stock(cod_pro: int, nuevo_stock):
        """F1-05: igual que actualizar_stock, pero como (query, params) para
        usar dentro de una transacción más grande (ver anular_orden)."""
        return ("UPDATE productos SET stock_pro = :1 WHERE cod_pro = :2", (nuevo_stock, cod_pro))

    async def listar_bienes_con_stock(self) -> List[Dict]:
        """Productos tipo BIEN activos con su stock (para inventario: entrada / toma física)."""
        return await self.execute(
            "SELECT cod_pro, nombre_pro, COALESCE(stock_pro, 0) AS stock_pro, stock_pro_min "
            "FROM productos "
            "WHERE COALESCE(cod_est_pro, 1) = 1 AND COALESCE(tipo_pro, 'BIEN') = 'BIEN' "
            "ORDER BY nombre_pro",
            None,
        )
