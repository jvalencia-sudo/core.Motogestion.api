import json
from typing import Dict, List, Optional
from repository.base_repository import BaseRepository


class OrdenAprobacionRepositorio(BaseRepository):
    """F2-03: aprobación de cotización (opcional por taller). Una sola fila
    vigente=true por orden, garantizado por un índice único parcial en la
    base de datos (ux_oac_vigente) -- esto además de la transacción."""

    def __init__(self):
        super().__init__(
            schema="",
            table_name="orden_aprobacion_cotizacion",
            primary_key="id_aprobacion",
            omit_key=True,
        )

    async def obtener_vigente(self, consecutivo_ot: int) -> Optional[Dict]:
        query = """
            SELECT * FROM orden_aprobacion_cotizacion
            WHERE consecutivo_ot = :1 AND vigente
        """
        return await self.get_one(query, (consecutivo_ot,))

    async def crear_aprobacion(
        self,
        consecutivo_ot: int,
        ip: Optional[str],
        user_agent: Optional[str],
        items_snapshot: List[dict],
        total_snapshot: float,
    ) -> Dict:
        """Marca cualquier aprobación previa de la orden como no vigente e
        inserta la nueva, en una sola transacción. El índice único parcial
        (ux_oac_vigente) es la garantía real contra una carrera de dos
        aprobaciones concurrentes -- esto solo evita dejar basura histórica
        con vigente=true duplicado si de todos modos ambas llegaran a pasar
        la validación de la capa de servicio."""
        statements = [
            (
                "UPDATE orden_aprobacion_cotizacion SET vigente = false "
                "WHERE consecutivo_ot = :1 AND vigente",
                (consecutivo_ot,),
            ),
            (
                "INSERT INTO orden_aprobacion_cotizacion "
                "(consecutivo_ot, ip, user_agent, items_snapshot, total_snapshot, vigente) "
                "VALUES (:1, :2, :3, :4::jsonb, :5, true)",
                (consecutivo_ot, ip, user_agent, json.dumps(items_snapshot), total_snapshot),
            ),
        ]
        await self.execute_transaction(statements)
        return await self.obtener_vigente(consecutivo_ot)

    async def invalidar_vigente(self, consecutivo_ot: int) -> bool:
        """Se llama cuando la cotización cambia (se agrega/retira/edita un
        ítem) -- la orden vuelve a requerir aprobación. En Python, no en
        trigger: ver la nota de diseño en el plan (duplicaría la lógica de
        vw_resumen_financiero_ot dentro de PL/pgSQL)."""
        query = "UPDATE orden_aprobacion_cotizacion SET vigente = false WHERE consecutivo_ot = :1 AND vigente"
        await self.execute_non_query(query, (consecutivo_ot,))
        return True
