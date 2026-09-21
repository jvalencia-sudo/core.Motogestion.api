from typing import Dict, List

from repository.base_repository import BaseRepository


class PlanRepositorio(BaseRepository):
    """Catálogo GLOBAL de planes (tabla `planes`, sin RLS)."""

    def __init__(self):
        super().__init__(
            schema="",
            table_name="planes",
            primary_key="cod_plan",
            omit_key=True,
            sequence_name="seq_planes",
        )

    async def listar(self) -> List[Dict]:
        return await self.execute(
            "SELECT cod_plan, nombre_plan, precio_plan, max_usuarios, max_motos, features, orden "
            "FROM planes ORDER BY orden",
            None,
        )

    async def get_por_nombre(self, nombre_plan: str) -> Dict:
        return await self.get_one(
            "SELECT cod_plan, nombre_plan, precio_plan, features FROM planes WHERE nombre_plan = :1",
            (nombre_plan,),
        )

    async def features_de(self, nombre_plan: str) -> Dict:
        """Flags de features de un plan (JSONB → dict). {} si no existe."""
        if not nombre_plan:
            return {}
        row = await self.get_one(
            "SELECT features FROM planes WHERE nombre_plan = :1", (nombre_plan,)
        )
        return (row.get("FEATURES") or {}) if row else {}
