from typing import Dict, List, Optional
from repository.base_repository import BaseRepository


class DetalleOrdenTrabajoRepositorio(BaseRepository):
    def __init__(self):
        super().__init__(
            schema="",
            table_name="detalle_orden_trabajo",
            primary_key="consecutivo_ot_deto",
            omit_key=False  # PK compuesta, se maneja manualmente
        )

    async def obtener_detalles_por_orden(self, consecutivo_ot: int) -> List[Dict]:
        """Obtiene todos los detalles de una orden usando vista"""
        query = """
            SELECT * FROM vw_detalle_ot_productos
            WHERE consecutivo_ot_deto = :1
            ORDER BY cod_pro_deto
        """
        return await self.execute(query, (consecutivo_ot,))

    async def crear_detalle(
        self,
        consecutivo_ot: int,
        cod_pro: int,
        cantidad: int,
        valor_unitario: int,
        documento_usu: str
    ) -> bool:
        """Crea un detalle de orden de trabajo"""
        query = """
            INSERT INTO detalle_orden_trabajo (
                consecutivo_ot_deto,
                cod_pro_deto,
                cantidad_deto,
                valor_unitario_deto,
                documento_usu_deto,
                fecha_confirmacion_deto
            ) VALUES (:1, :2, :3, :4, :5, CURRENT_DATE)
        """
        await self.execute_non_query(query, (consecutivo_ot, cod_pro, cantidad, valor_unitario, documento_usu))
        return True

    async def existe_detalle(self, consecutivo_ot: int, cod_pro: int) -> bool:
        """Verifica si existe un detalle especifico en la orden"""
        query = """
            SELECT COUNT(*) AS count
            FROM detalle_orden_trabajo
            WHERE consecutivo_ot_deto = :1 AND cod_pro_deto = :2
        """
        result = await self.get_one(query, (consecutivo_ot, cod_pro))
        return result and result.get('COUNT', 0) > 0

    async def actualizar_cantidad_detalle(
        self,
        consecutivo_ot: int,
        cod_pro: int,
        nueva_cantidad: int
    ) -> bool:
        """Actualiza la cantidad de un producto en el detalle"""
        query = """
            UPDATE detalle_orden_trabajo
            SET cantidad_deto = :1
            WHERE consecutivo_ot_deto = :2 AND cod_pro_deto = :3
        """
        await self.execute_non_query(query, (nueva_cantidad, consecutivo_ot, cod_pro))
        return True

    async def eliminar_detalle(self, consecutivo_ot: int, cod_pro: int) -> bool:
        """Elimina un producto del detalle de la orden"""
        query = """
            DELETE FROM detalle_orden_trabajo
            WHERE consecutivo_ot_deto = :1 AND cod_pro_deto = :2
        """
        await self.execute_non_query(query, (consecutivo_ot, cod_pro))
        return True

    async def obtener_detalle(self, consecutivo_ot: int, cod_pro: int) -> Optional[Dict]:
        """Obtiene un detalle especifico"""
        query = """
            SELECT * FROM detalle_orden_trabajo
            WHERE consecutivo_ot_deto = :1 AND cod_pro_deto = :2
        """
        return await self.get_one(query, (consecutivo_ot, cod_pro))
