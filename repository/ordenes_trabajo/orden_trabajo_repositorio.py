from typing import Dict, List, Optional
from repository.base_repository import BaseRepository


class OrdenTrabajoRepositorio(BaseRepository):
    def __init__(self):
        super().__init__(
            schema="",
            table_name="ordenes_trabajo",
            primary_key="consecutivo_ot",
            omit_key=True  # consecutivo_ot se genera con trigger tg_gen_consecutivo_ot (MAX+1)
        )

    async def obtener_ordenes_completas(self) -> List[Dict]:
        """Obtiene todas las ordenes de trabajo con informacion completa usando vista"""
        query = "SELECT * FROM vw_ordenes_trabajo_completa ORDER BY consecutivo_ot DESC"
        return await self.execute(query, None)

    async def obtener_orden_por_id(self, consecutivo_ot: int) -> Optional[Dict]:
        """Obtiene una orden de trabajo por su consecutivo usando vista"""
        query = "SELECT * FROM vw_ordenes_trabajo_completa WHERE consecutivo_ot = :1"
        return await self.get_one(query, (consecutivo_ot,))

    async def obtener_ordenes_pendientes(self) -> List[Dict]:
        """Obtiene todas las ordenes pendientes de entrega usando vista"""
        query = "SELECT * FROM vw_ot_pendientes ORDER BY dias_pendiente DESC"
        return await self.execute(query, None)

    async def obtener_ordenes_por_cliente(self, documento_cli: str) -> List[Dict]:
        """Obtiene todas las ordenes de un cliente especifico"""
        query = """
            SELECT * FROM vw_ordenes_trabajo_completa
            WHERE documento_cli = :1
            ORDER BY consecutivo_ot DESC
        """
        return await self.execute(query, (documento_cli,))

    async def obtener_ordenes_por_moto(self, placa_mot: str) -> List[Dict]:
        """Obtiene todas las ordenes de una moto especifica"""
        query = """
            SELECT * FROM vw_ordenes_trabajo_completa
            WHERE placa_mot = :1
            ORDER BY consecutivo_ot DESC
        """
        return await self.execute(query, (placa_mot,))

    async def obtener_resumen_financiero(self, consecutivo_ot: int) -> Optional[Dict]:
        """Obtiene el resumen financiero de una orden usando vista"""
        query = "SELECT * FROM vw_resumen_financiero_ot WHERE consecutivo_ot = :1"
        return await self.get_one(query, (consecutivo_ot,))

    async def actualizar_estado(self, consecutivo_ot: int, cod_estado: int) -> bool:
        """Actualiza el estado de una orden de trabajo"""
        query = """
            UPDATE ordenes_trabajo
            SET cod_ot_est_ot = :1
            WHERE consecutivo_ot = :2
        """
        await self.execute(query, (cod_estado, consecutivo_ot))
        return True

    async def registrar_entrega(
        self,
        consecutivo_ot: int,
        fecha_entrega,
        km_salida: Optional[int],
        fecha_fin_garantia
    ) -> bool:
        """Registra la entrega de una orden de trabajo"""
        query = """
            UPDATE ordenes_trabajo
            SET fecha_entrega_ot = :1,
                kilometreje_salida_ot = :2,
                cod_ot_est_ot = 4,
                fecha_fin_garantia_ot = :3
            WHERE consecutivo_ot = :4
        """
        await self.execute(query, (fecha_entrega, km_salida, fecha_fin_garantia, consecutivo_ot))
        return True

    async def existe_orden(self, consecutivo_ot: int) -> bool:
        """Verifica si existe una orden de trabajo"""
        query = "SELECT COUNT(*) AS count FROM ordenes_trabajo WHERE consecutivo_ot = :1"
        result = await self.get_one(query, (consecutivo_ot,))
        return result and result.get('COUNT', 0) > 0

    async def actualizar_campos(self, consecutivo_ot: int, campos: dict) -> bool:
        """Actualiza campos específicos de una orden de trabajo"""
        # Construir SET clause dinámicamente
        set_clauses = []
        params = []

        for campo, valor in campos.items():
            if campo != 'CONSECUTIVO_OT':  # Excluir primary key
                set_clauses.append(f"{campo} = :{len(params) + 1}")
                params.append(valor)

        if not set_clauses:
            return True

        # Agregar consecutivo_ot al final de params
        params.append(consecutivo_ot)

        query = f"""
            UPDATE ordenes_trabajo
            SET {', '.join(set_clauses)}
            WHERE consecutivo_ot = :{len(params)}
        """

        await self.execute_non_query(query, tuple(params))
        return True

    async def obtener_orden_anterior(self, placa_mot: str, consecutivo_ot: int) -> Optional[Dict]:
        """Obtiene la orden anterior entregada de una moto (excluyendo la orden actual)"""
        query = """
            SELECT fecha_fin_garantia_ot, fecha_entrega_ot
            FROM ordenes_trabajo
            WHERE placa_mot_ot = :1
              AND consecutivo_ot != :2
              AND fecha_entrega_ot IS NOT NULL
            ORDER BY fecha_entrega_ot DESC
            FETCH FIRST 1 ROW ONLY
        """
        return await self.get_one(query, (placa_mot, consecutivo_ot))
