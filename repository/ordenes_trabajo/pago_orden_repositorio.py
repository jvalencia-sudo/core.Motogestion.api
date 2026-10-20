from typing import Dict, List, Optional
from repository.base_repository import BaseRepository


class PagoOrdenRepositorio(BaseRepository):
    def __init__(self):
        super().__init__(
            schema="",
            table_name="pagos_orden",
            primary_key="cod_pago_orden",
            omit_key=True,  # cod_pago_orden se genera con secuencia
            sequence_name="seq_pagos_orden"
        )

    async def obtener_por_id(self, cod_pago_orden: int) -> Optional[Dict]:
        """Obtiene un pago por su código usando la vista (trae el nombre del usuario)."""
        query = "SELECT * FROM vw_pagos_orden WHERE cod_pago_orden = :1"
        return await self.get_one(query, (cod_pago_orden,))

    async def listar_por_orden(self, consecutivo_ot: int) -> List[Dict]:
        """Lista los abonos de una orden, del más reciente al más antiguo."""
        query = """
            SELECT * FROM vw_pagos_orden
            WHERE consecutivo_ot_pago = :1
            ORDER BY fecha_pago DESC
        """
        return await self.execute(query, (consecutivo_ot,))

    async def anular(self, cod_pago_orden: int, motivo: str, documento_usu: str) -> bool:
        """Anula un pago (motivo obligatorio). Los pagos no se editan ni se
        borran -- este es el único UPDATE permitido sobre la tabla."""
        query = """
            UPDATE pagos_orden
            SET anulado_pago = true,
                motivo_anulacion_pago = :1,
                fecha_anulacion_pago = now(),
                documento_usu_anulacion_pago = :2
            WHERE cod_pago_orden = :3
        """
        await self.execute_non_query(query, (motivo, documento_usu, cod_pago_orden))
        return True
