from typing import Dict, List
from repository.base_repository import BaseRepository


class PermisoRepositorio(BaseRepository):
    def __init__(self):
        super().__init__(
            schema="auth",
            table_name="permisos",
            primary_key="cod_prm",
            omit_key=True,
            sequence_name="seq_permisos"
        )

    async def obtener_permisos_por_perfil(self, cod_prf: int, cod_rol_prf: int) -> List[Dict]:
        # Lee la vista de dominio (permisos + su asignación); no cruza tablas base.
        return await self.execute(
            "SELECT cod_prm, nombre_prm, descripcion_prm, ruta_vis_prm "
            "FROM vw_permisos_por_perfil "
            "WHERE cod_prf_pp = :1 AND cod_rol_prf_pp = :2 AND cod_est_pp = 1",
            (cod_prf, cod_rol_prf),
        )


    async def obtener_vw_permisos(self) -> List[Dict]:
        return await self.execute("select * from vw_permisos order by nombre_prm", None)
