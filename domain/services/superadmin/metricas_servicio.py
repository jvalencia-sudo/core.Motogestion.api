from typing import Dict

from infrastructure.utils.tenant_context import reset_tenant, set_tenant
from repository.superadmin.metricas_repositorio import MetricasRepositorio
from repository.talleres.taller_repositorio import TallerRepositorio


class MetricasServicio:
    """Métricas de uso por taller (F0-14), sin ningún rol BYPASSRLS: recorre los
    talleres (tabla sin RLS) y, por cada uno, fija app.tenant_id para que las
    consultas a tablas CON RLS (ordenes_trabajo, usuarios, audit_log) vean solo
    ese taller. O(N talleres) secuencial -- aceptable a la escala del piloto.

    Cada iteración restaura el tenant anterior al salir (ver tenant_context.py)
    -- no por el request SIGUIENTE (resolve_tenant ya lo fija de cero), sino
    por si DENTRO del mismo request, después de pedir métricas, se hace otra
    consulta a una tabla con RLS: sin restaurar, esa consulta vería el taller
    del último recorrido, no el del caller, sin ningún aviso."""

    def __init__(self):
        self.taller_repo = TallerRepositorio()
        self.metricas_repo = MetricasRepositorio()

    async def metricas_de_todos_los_talleres(self) -> Dict[int, Dict]:
        talleres = await self.taller_repo.get_all()
        resultado: Dict[int, Dict] = {}
        for t in talleres:
            cod_taller = t.get("COD_TALLER")
            resultado[cod_taller] = await self.metricas_de_un_taller(cod_taller)
        return resultado

    async def metricas_de_un_taller(self, cod_taller: int) -> Dict:
        token = set_tenant(cod_taller)
        try:
            return {
                "ordenes_7d": await self.metricas_repo.contar_ordenes_periodo(7),
                "ordenes_30d": await self.metricas_repo.contar_ordenes_periodo(30),
                "usuarios_activos": await self.metricas_repo.contar_usuarios_activos(),
                "ultima_actividad": await self.metricas_repo.fecha_ultima_actividad(),
            }
        finally:
            reset_tenant(token)
