from typing import Dict, List, Optional

from repository.base_repository import BaseRepository


class PagoRepositorio(BaseRepository):
    """Tabla `pagos` (billing de plataforma, SIN RLS). El webhook la consulta por
    referencia sin contexto de tenant."""

    def __init__(self):
        super().__init__(
            schema="",
            table_name="pagos",
            primary_key="cod_pago",
            omit_key=True,
            sequence_name="seq_pagos",
        )

    async def crear_pendiente(
        self, cod_taller: int, nombre_plan: str, monto: int, referencia: str
    ) -> int:
        res = await self.db.insert(
            "INSERT INTO pagos (cod_taller, nombre_plan, monto, referencia) "
            "VALUES (:1, :2, :3, :4)",
            (cod_taller, nombre_plan, monto, referencia),
            primary_key="cod_pago",
        )
        return res["cod_pago"]

    async def get_por_referencia(self, referencia: str) -> Optional[Dict]:
        return await self.db.get_first(
            "SELECT cod_pago, cod_taller, nombre_plan, monto, estado "
            "FROM pagos WHERE referencia = :1",
            (referencia,),
        )

    async def marcar_estado(
        self, referencia: str, estado: str, transaction_id: Optional[str] = None
    ) -> None:
        await self.db.execute_non_query(
            "UPDATE pagos SET estado = :1, wompi_transaction_id = :2 WHERE referencia = :3",
            (estado, transaction_id, referencia),
        )

    async def listar_por_taller(self, cod_taller: int) -> List[Dict]:
        return await self.db.execute(
            "SELECT cod_pago, nombre_plan, monto, estado, "
            "to_char(fecha, 'YYYY-MM-DD HH24:MI') AS fecha "
            "FROM pagos WHERE cod_taller = :1 ORDER BY fecha DESC",
            (cod_taller,),
        )
