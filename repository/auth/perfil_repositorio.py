from typing import Dict, Optional, List
from repository.base_repository import BaseRepository


class PerfilRepositorio(BaseRepository):
    def __init__(self):
        super().__init__(
            schema="auth",
            table_name="perfiles",
            primary_key="cod_prf",
            omit_key=True,
            sequence_name="seq_perfiles"
        )



    async def obtener_vw_perfiles(self) -> List[Dict]:
        """Obtiene todos los perfiles con información de rol y estado desde la vista"""
        return await self.execute("SELECT * FROM vw_perfiles ORDER BY cod_prf", None)

    async def actualizar_estado(self, cod_prf: int, cod_est_prf: int) -> None:
        """Actualiza el estado de un perfil (activar/desactivar)"""
        query = """
            UPDATE perfiles
            SET cod_est_prf = :1
            WHERE cod_prf = :2
        """
        await self.execute_non_query(query, (cod_est_prf, cod_prf))

    async def verificar_perfil_existe(self, cod_prf: int) -> Optional[Dict]:
        """Verifica si existe un perfil por su código"""
        return await self.get_by_id(cod_prf)
