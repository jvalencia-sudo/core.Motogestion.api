from typing import Optional

from repository.base_repository import BaseRepository


class MetricasRepositorio(BaseRepository):
    """Métricas de uso de UN taller (F0-14). Cada método asume que el caller ya
    fijó app.tenant_id a ese taller (ver metricas_servicio.py) -- estas tablas SÍ
    tienen RLS, a diferencia de talleres/pagos."""

    def __init__(self):
        super().__init__(schema="", table_name="ordenes_trabajo", primary_key="consecutivo_ot", omit_key=True)

    async def contar_ordenes_periodo(self, dias: int) -> int:
        row = await self.db.get_first(
            "SELECT count(*) AS total FROM ordenes_trabajo "
            "WHERE fecha_elaboracion_ot >= CURRENT_DATE - make_interval(days => :1)",
            (dias,),
        )
        return (row.get("TOTAL") or 0) if row else 0

    async def contar_usuarios_activos(self) -> int:
        row = await self.db.get_first(
            "SELECT count(*) AS total FROM usuarios WHERE cod_est_usu = 1", None
        )
        return (row.get("TOTAL") or 0) if row else 0

    async def fecha_ultima_actividad(self) -> Optional[str]:
        """Último evento en audit_log del taller (reusa el trigger fn_audit, que ya
        registra inserts/updates de clientes/productos/órdenes/usuarios) en vez de
        inventar un last_login/updated_at nuevo."""
        row = await self.db.get_first(
            "SELECT to_char(max(fecha), 'YYYY-MM-DD HH24:MI') AS ultima FROM audit_log", None
        )
        return row.get("ULTIMA") if row else None
