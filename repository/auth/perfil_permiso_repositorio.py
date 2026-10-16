from typing import Dict, List, Optional

from psycopg.types.json import Jsonb

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
        """Obtiene permisos asignados a un perfil específico desde la vista.
        Filtra por cod_rol directo (la vista ya lo expone; sin subconsulta a `roles`)."""
        query = """
            SELECT * FROM vw_perfiles_permisos_detalle
            WHERE cod_prf = :1 AND cod_rol = :2
            ORDER BY nombre_prm
        """
        return await self.execute(query, (cod_prf, cod_rol))

    async def obtener_cod_prm_asignados(self, cod_prf: int, cod_rol: int) -> List[Dict]:
        """Códigos de permiso ya asignados a un perfil (cualquier estado). Su propia tabla."""
        return await self.execute(
            "SELECT cod_prm_pp FROM perfiles_permisos "
            "WHERE cod_prf_pp = :1 AND cod_rol_prf_pp = :2",
            (cod_prf, cod_rol),
        )

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

    async def reemplazar_permisos(
        self, cod_prf: int, cod_rol: int, cod_prm_list: List[int], usuario: str
    ) -> None:
        """Reemplaza TODOS los permisos de un perfil en una sola transacción
        (DELETE + INSERT por cada permiso nuevo + entrada de auditoría): o
        queda todo aplicado, o no queda nada a medias si algo falla."""
        statements: List = [
            (
                "DELETE FROM perfiles_permisos WHERE cod_prf_pp = :1 AND cod_rol_prf_pp = :2",
                (cod_prf, cod_rol),
            )
        ]
        for cod_prm in cod_prm_list:
            statements.append((
                "INSERT INTO perfiles_permisos (cod_prm_pp, cod_prf_pp, cod_rol_prf_pp, cod_est_pp) "
                "VALUES (:1, :2, :3, 1)",
                (cod_prm, cod_prf, cod_rol),
            ))
        statements.append((
            "INSERT INTO audit_log (cod_taller, usuario, tabla, evento, valor_nuevo) "
            "VALUES (current_setting('app.tenant_id')::integer, :1, 'perfiles_permisos', 'U', :2)",
            (usuario, Jsonb({"cod_prf": cod_prf, "cod_rol": cod_rol, "cod_prm_list": cod_prm_list})),
        ))
        await self.execute_transaction(statements)

