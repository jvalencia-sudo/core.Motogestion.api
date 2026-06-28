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
        return await self.get_one(
            """
            SELECT
              (SELECT count(*) FROM clientes)        AS total_clientes,
              (SELECT count(*) FROM motos)           AS total_motos,
              (SELECT count(*) FROM productos)       AS total_productos,
              (SELECT count(*) FROM ordenes_trabajo) AS total_ordenes,
              (SELECT count(*) FROM ordenes_trabajo WHERE cod_ot_est_ot IN (1, 2, 6)) AS ot_activas,
              (SELECT count(*) FROM productos
                 WHERE cod_est_pro = 1 AND stock_pro <= stock_pro_min)               AS productos_bajo_stock,
              (SELECT count(*) FROM reclamos)        AS total_reclamos
            """,
            None,
        )

    async def ordenes_por_estado(self) -> List[Dict]:
        return await self.execute(
            """
            SELECT e.cod_ot_est, e.nombre_ot_est, COUNT(o.consecutivo_ot) AS cantidad
            FROM ot_estados e
            LEFT JOIN ordenes_trabajo o ON o.cod_ot_est_ot = e.cod_ot_est
            GROUP BY e.cod_ot_est, e.nombre_ot_est
            ORDER BY e.cod_ot_est
            """,
            None,
        )
