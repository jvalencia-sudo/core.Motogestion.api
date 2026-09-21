from typing import Dict, List

from repository.base_repository import BaseRepository


class DashboardRepositorio(BaseRepository):
    """Consultas agregadas para la home. Las tablas por-taller las acota el RLS
    (app.tenant_id ya fijado por resolve_tenant), así que cada taller ve solo lo suyo."""

    def __init__(self):
        super().__init__(
            schema="",
            table_name="ordenes_trabajo",
            primary_key="consecutivo_ot",
            omit_key=True,
        )

    async def resumen_escalares(self) -> Dict:
        # Lee la vista de dominio (agrega varias tablas; el RLS acota por taller).
        return await self.get_one("SELECT * FROM vw_dashboard_resumen", None)

    async def ordenes_por_estado(self) -> List[Dict]:
        return await self.execute(
            "SELECT cod_ot_est, nombre_ot_est, cantidad "
            "FROM vw_dashboard_ordenes_por_estado ORDER BY cod_ot_est",
            None,
        )
