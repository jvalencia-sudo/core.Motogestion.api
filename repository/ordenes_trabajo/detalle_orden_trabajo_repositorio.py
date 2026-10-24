from decimal import Decimal
from typing import Dict, List, Optional, Union
from repository.base_repository import BaseRepository

Cantidad = Union[int, Decimal]


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
        cantidad: Cantidad,
        valor_unitario: int,
        documento_usu: str,
        cobrar: bool = True,
        motivo_no_cobro: Optional[str] = None,
    ) -> bool:
        """Crea un detalle de orden de trabajo"""
        query = """
            INSERT INTO detalle_orden_trabajo (
                consecutivo_ot_deto,
                cod_pro_deto,
                cantidad_deto,
                valor_unitario_deto,
                documento_usu_deto,
                fecha_confirmacion_deto,
                cobrar_deto,
                motivo_no_cobro_deto
            ) VALUES (:1, :2, :3, :4, :5, CURRENT_DATE, :6, :7)
        """
        await self.execute_non_query(
            query, (consecutivo_ot, cod_pro, cantidad, valor_unitario, documento_usu, cobrar, motivo_no_cobro)
        )
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
        nueva_cantidad: Cantidad,
        cobrar: bool = True,
        motivo_no_cobro: Optional[str] = None,
    ) -> bool:
        """Actualiza la cantidad (y el estado de cobro) de un producto en el detalle"""
        query = """
            UPDATE detalle_orden_trabajo
            SET cantidad_deto = :1, cobrar_deto = :2, motivo_no_cobro_deto = :3
            WHERE consecutivo_ot_deto = :4 AND cod_pro_deto = :5
        """
        await self.execute_non_query(query, (nueva_cantidad, cobrar, motivo_no_cobro, consecutivo_ot, cod_pro))
        return True

    async def retirar_detalle(self, consecutivo_ot: int, cod_pro: int, motivo: str) -> bool:
        """F2-02: retira un producto del detalle (soft-delete, con motivo).
        No borra la fila -- la deja visible (tachada) para el taller y el
        cliente. El `AND NOT retirado` evita retirar dos veces la misma fila
        (y con eso, una doble reversa de stock por el trigger). Devuelve
        False si la fila no existe o ya estaba retirada."""
        query = """
            UPDATE detalle_orden_trabajo
            SET retirado = true, motivo_retiro = :1
            WHERE consecutivo_ot_deto = :2 AND cod_pro_deto = :3 AND NOT retirado
        """
        resultado = await self.db.insert(query, (motivo, consecutivo_ot, cod_pro))
        return bool(resultado and resultado.get("affected_rows"))

    async def obtener_detalle(self, consecutivo_ot: int, cod_pro: int) -> Optional[Dict]:
        """Obtiene un detalle especifico"""
        query = """
            SELECT * FROM detalle_orden_trabajo
            WHERE consecutivo_ot_deto = :1 AND cod_pro_deto = :2
        """
        return await self.get_one(query, (consecutivo_ot, cod_pro))
