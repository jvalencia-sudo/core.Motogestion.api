import secrets
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
            "SELECT cod_pago, nombre_plan, monto, estado, medio, detalle_medio, "
            "to_char(fecha, 'YYYY-MM-DD HH24:MI') AS fecha "
            "FROM pagos WHERE cod_taller = :1 ORDER BY fecha DESC",
            (cod_taller,),
        )

    async def crear_aprobado_manual(
        self, cod_taller: int, nombre_plan: str, monto: int, detalle_medio: str
    ) -> int:
        """Registra un pago manual (efectivo/transferencia/Nequi) ya APROBADO --
        no pasa por Wompi ni por una referencia de checkout (F0-14)."""
        res = await self.db.insert(
            "INSERT INTO pagos (cod_taller, nombre_plan, monto, referencia, estado, medio, detalle_medio) "
            "VALUES (:1, :2, :3, :4, 'APPROVED', 'MANUAL', :5)",
            (cod_taller, nombre_plan, monto, f"MANUAL-{cod_taller}-{secrets.token_hex(6)}", detalle_medio),
            primary_key="cod_pago",
        )
        return res["cod_pago"]

    async def listar_todos(self, estado: Optional[str] = None, medio: Optional[str] = None) -> List[Dict]:
        """Pagos de TODOS los talleres, para el panel de super-admin (F0-14).
        pagos no tiene RLS: filtra solo por los parámetros dados."""
        condiciones, params = [], []
        if estado:
            condiciones.append(f"estado = :{len(params) + 1}")
            params.append(estado)
        if medio:
            condiciones.append(f"medio = :{len(params) + 1}")
            params.append(medio)
        where = f"WHERE {' AND '.join(condiciones)}" if condiciones else ""
        return await self.db.execute(
            f"SELECT p.cod_pago, p.cod_taller, t.nombre_tal, p.nombre_plan, p.monto, "
            f"p.estado, p.medio, p.detalle_medio, "
            f"to_char(p.fecha, 'YYYY-MM-DD HH24:MI') AS fecha "
            f"FROM pagos p JOIN talleres t ON t.cod_taller = p.cod_taller "
            f"{where} ORDER BY p.fecha DESC",
            tuple(params),
        )

    async def listar_aprobados_sin_suscripcion_activa(self) -> List[Dict]:
        """Alerta: pago APROBADO cuyo taller hoy no está 'activo' (pudo haberse
        suspendido después, o el pago nunca llegó a activar la suscripción)."""
        return await self.db.execute(
            "SELECT p.cod_pago, p.cod_taller, t.nombre_tal, p.monto, "
            "to_char(p.fecha, 'YYYY-MM-DD HH24:MI') AS fecha "
            "FROM pagos p JOIN talleres t ON t.cod_taller = p.cod_taller "
            "WHERE p.estado = 'APPROVED' AND t.estado_tal != 'activo'",
            None,
        )

    async def listar_pendientes_viejos(self, horas: int = 24) -> List[Dict]:
        """Alerta: pago PENDING hace más de `horas` (probablemente abandonado)."""
        return await self.db.execute(
            "SELECT p.cod_pago, p.cod_taller, t.nombre_tal, p.monto, "
            "to_char(p.fecha, 'YYYY-MM-DD HH24:MI') AS fecha "
            "FROM pagos p JOIN talleres t ON t.cod_taller = p.cod_taller "
            "WHERE p.estado = 'PENDING' AND p.fecha < now() - make_interval(hours => :1)",
            (horas,),
        )
