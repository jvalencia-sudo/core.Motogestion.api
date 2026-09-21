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

    async def sembrar_taller(self) -> None:
        """Siembra los perfiles por defecto del taller actual (Admin/Mecánico/
        Recepcionista) con sus permisos, vía fn_seed_perfiles_taller. El taller se
        toma del contexto (app.tenant_id, ya fijado por el servicio)."""
        await self.execute_non_query(
            "SELECT fn_seed_perfiles_taller(current_setting('app.tenant_id')::integer)",
            None,
        )

    async def obtener_cod_admin(self) -> Optional[int]:
        """cod_prf del perfil con rol Admin (cod_rol_prf = 1) del taller actual."""
        row = await self.get_one(
            "SELECT cod_prf FROM perfiles WHERE cod_rol_prf = 1 LIMIT 1", None
        )
        return row.get("COD_PRF") if row else None

    async def get_nombre(self, cod_prf: int) -> Optional[str]:
        """Nombre de un perfil (acotado por RLS al taller actual; cod_prf es único global)."""
        row = await self.get_one(
            "SELECT nombre_prf FROM perfiles WHERE cod_prf = :1 LIMIT 1", (cod_prf,)
        )
        return row.get("NOMBRE_PRF") if row else None
