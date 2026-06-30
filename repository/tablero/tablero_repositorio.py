from typing import Dict, List, Optional

from repository.base_repository import BaseRepository


class TableroRepositorio(BaseRepository):
    """El tablero muestra las órdenes de trabajo (vw_ordenes_trabajo_completa,
    security_invoker → respeta el RLS del taller). El filtro por mecánico lo decide
    el servicio según el rol del usuario."""

    def __init__(self):
        super().__init__(
            schema="",
            table_name="ordenes_trabajo",
            primary_key="consecutivo_ot",
            omit_key=True,
        )

    async def listar_mecanicos(self) -> List[Dict]:
        return await self.execute(
            "select documento_usu, "
            "       nombre_usu || ' ' || coalesce(apellido_1_usu, '') as nombre "
            "from usuarios "
            "where cod_rol_prf_usu = 2 and cod_est_usu = 1 "
            "order by nombre_usu",
            None,
        )

    async def listar_ordenes(self, documento_mecanico: Optional[str]) -> List[Dict]:
        # Tablero Kanban: todas las OT del taller (todos los estados). Más antiguas primero.
        base = (
            "select consecutivo_ot, fecha_elaboracion_ot, placa_mot, marca_moto, "
            "       nombre_completo_cliente, observacion_ot, estado_ot, cod_ot_est_ot, "
            "       mecanico, documento_mecanico "
            "from vw_ordenes_trabajo_completa "
        )
        orden = " order by fecha_elaboracion_ot asc nulls last, consecutivo_ot"
        if documento_mecanico:
            return await self.execute(
                base + "where documento_mecanico = :1" + orden,
                (documento_mecanico,),
            )
        return await self.execute(base + orden, None)

    async def get_ot_mecanico(self, consecutivo_ot: int) -> Optional[Dict]:
        """Mecánico asignado a la OT (para validar propiedad). RLS acota al taller."""
        return await self.get_one(
            "select documento_usu_mc_ot, cod_ot_est_ot from ordenes_trabajo "
            "where consecutivo_ot = :1",
            (consecutivo_ot,),
        )

    async def actualizar_estado(self, consecutivo_ot: int, cod_estado: int) -> None:
        await self.execute_non_query(
            "update ordenes_trabajo set cod_ot_est_ot = :1 where consecutivo_ot = :2",
            (cod_estado, consecutivo_ot),
        )
