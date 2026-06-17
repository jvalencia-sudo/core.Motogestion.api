from typing import Dict, List, Optional
from repository.base_repository import BaseRepository


class PerfilPermisoRepositorio(BaseRepository):
    def __init__(self):
        # omit_key=False porque cod_prm_pp no es autoincremental
        # Es parte de una llave primaria compuesta que debe insertarse manualmente
        super().__init__("auth", "perfiles_permisos", "cod_prm_pp", omit_key=False)

    async def obtener_vw_perfiles_permisos_detalle(self) -> List[Dict]:
        """Obtiene todos los perfiles con sus permisos desde la vista"""
        return await self.execute("SELECT * FROM vw_perfiles_permisos_detalle ORDER BY cod_prf, cod_prm", None)

    async def obtener_permisos_por_perfil(self, cod_prf: int, cod_rol: int) -> List[Dict]:
        """Obtiene permisos asignados a un perfil específico desde la vista"""
        query = """
            SELECT * FROM vw_perfiles_permisos_detalle
            WHERE cod_prf = :1 AND nombre_rol = (SELECT nombre_rol FROM roles WHERE cod_rol = :2)
            ORDER BY nombre_prm
        """
        return await self.execute(query, (cod_prf, cod_rol))

    async def verificar_permiso_existe(self, cod_prf: int, cod_rol: int, cod_prm: int) -> Optional[Dict]:
        """Verifica si un permiso ya está asignado a un perfil usando get_by_multiple_fields"""
        results = await self.get_by_multiple_fields({
            'cod_prf_pp': cod_prf,
            'cod_rol_prf_pp': cod_rol,
            'cod_prm_pp': cod_prm
        })
        return results[0] if results else None

    async def actualizar_estado_permiso(self, cod_prf: int, cod_rol: int, cod_prm: int, cod_est: int) -> None:
        """Actualiza el estado de un permiso (activar/desactivar)"""
        query = """
            UPDATE perfiles_permisos
            SET cod_est_pp = :1
            WHERE cod_prf_pp = :2 AND cod_rol_prf_pp = :3 AND cod_prm_pp = :4
        """
        await self.execute_non_query(query, (cod_est, cod_prf, cod_rol, cod_prm))

    async def obtener_permisos_disponibles(self, cod_prf: int, cod_rol: int) -> List[Dict]:
        """Obtiene permisos que NO están asignados al perfil"""
        query = """
            SELECT p.*
            FROM permisos p
            WHERE NOT EXISTS (
                SELECT 1 FROM perfiles_permisos pp
                WHERE pp.cod_prm_pp = p.cod_prm
                AND pp.cod_prf_pp = :1
                AND pp.cod_rol_prf_pp = :2
            )
            ORDER BY p.nombre_prm
        """
        return await self.execute(query, (cod_prf, cod_rol))
