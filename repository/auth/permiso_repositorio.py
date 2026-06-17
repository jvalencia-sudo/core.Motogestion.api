from typing import Dict, Optional, List
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
        return await self.execute(
            """
            SELECT p.*
            FROM permisos p
            INNER JOIN perfiles_permisos pp ON p.cod_prm = pp.cod_prm_pp
            WHERE pp.cod_prf_pp = :1
            AND pp.cod_rol_prf_pp = :2
            AND pp.cod_est_pp = 1
            """,
            (cod_prf, cod_rol_prf),
        )


    async def obtener_vw_permisos(self)->List[Dict]:
        return await self.execute("select * from vw_permisos order by cod_rol_prm")
