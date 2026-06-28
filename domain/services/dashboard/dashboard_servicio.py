from domain.models.dashboard.dashboard_model import OrdenPorEstado, ResumenDashboard
from repository.dashboard.dashboard_repositorio import DashboardRepositorio


class DashboardServicio:
    def __init__(self):
        self.repo = DashboardRepositorio()

    async def resumen(self) -> ResumenDashboard:
        esc = await self.repo.resumen_escalares() or {}
        por_estado = await self.repo.ordenes_por_estado()

        def n(key: str) -> int:
            return int(esc.get(key) or 0)

        return ResumenDashboard(
            total_clientes=n("TOTAL_CLIENTES"),
            total_motos=n("TOTAL_MOTOS"),
            total_productos=n("TOTAL_PRODUCTOS"),
            total_ordenes=n("TOTAL_ORDENES"),
            ot_activas=n("OT_ACTIVAS"),
            productos_bajo_stock=n("PRODUCTOS_BAJO_STOCK"),
            total_reclamos=n("TOTAL_RECLAMOS"),
            ordenes_por_estado=[
                OrdenPorEstado(
                    cod_ot_est=r.get("COD_OT_EST"),
                    nombre_ot_est=r.get("NOMBRE_OT_EST"),
                    cantidad=int(r.get("CANTIDAD") or 0),
                )
                for r in por_estado
            ],
        )
