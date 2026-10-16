from typing import List, Optional

from domain.contracts.superadmin.pago_superadmin_contract import (
    AlertaPagoContract,
    AlertasPagoContract,
    PagoPlataformaContract,
)
from repository.pagos.pago_repositorio import PagoRepositorio


class PagosSuperAdminServicio:
    """Pagos de TODOS los talleres y alertas de casos raros, para el panel de
    super-admin (F0-14). pagos no tiene RLS: se consulta directo."""

    def __init__(self):
        self.pago_repo = PagoRepositorio()

    async def listar(self, estado: Optional[str] = None, medio: Optional[str] = None) -> List[PagoPlataformaContract]:
        filas = await self.pago_repo.listar_todos(estado, medio)
        return [
            PagoPlataformaContract(
                cod_pago=f.get("COD_PAGO"), cod_taller=f.get("COD_TALLER"), nombre_tal=f.get("NOMBRE_TAL"),
                nombre_plan=f.get("NOMBRE_PLAN"), monto=f.get("MONTO"), estado=f.get("ESTADO"),
                medio=f.get("MEDIO"), detalle_medio=f.get("DETALLE_MEDIO"), fecha=f.get("FECHA"),
            )
            for f in filas
        ]

    async def alertas(self) -> AlertasPagoContract:
        aprobados = await self.pago_repo.listar_aprobados_sin_suscripcion_activa()
        pendientes = await self.pago_repo.listar_pendientes_viejos(24)
        return AlertasPagoContract(
            aprobados_sin_suscripcion_activa=[self._a_alerta(f) for f in aprobados],
            pendientes_viejos=[self._a_alerta(f) for f in pendientes],
        )

    @staticmethod
    def _a_alerta(f: dict) -> AlertaPagoContract:
        return AlertaPagoContract(
            cod_pago=f.get("COD_PAGO"), cod_taller=f.get("COD_TALLER"),
            nombre_tal=f.get("NOMBRE_TAL"), monto=f.get("MONTO"), fecha=f.get("FECHA"),
        )
