from typing import Dict, Optional, List

from psycopg.types.json import Jsonb

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
        """cod_prf del perfil Administrador (es_admin = true) del taller actual."""
        row = await self.get_one(
            "SELECT cod_prf FROM perfiles WHERE es_admin = true LIMIT 1", None
        )
        return row.get("COD_PRF") if row else None

    async def get_nombre(self, cod_prf: int) -> Optional[str]:
        """Nombre de un perfil (acotado por RLS al taller actual; cod_prf es único global)."""
        row = await self.get_one(
            "SELECT nombre_prf FROM perfiles WHERE cod_prf = :1 LIMIT 1", (cod_prf,)
        )
        return row.get("NOMBRE_PRF") if row else None

    async def es_perfil_admin(self, cod_prf: int) -> Optional[bool]:
        """es_admin del perfil, o None si no existe (RLS ya acota al taller
        del caller: si cod_prf es de otro taller, no devuelve nada -- mismo
        patrón que get_nombre)."""
        row = await self.get_one(
            "SELECT es_admin FROM perfiles WHERE cod_prf = :1 LIMIT 1", (cod_prf,)
        )
        return bool(row.get("ES_ADMIN")) if row else None

    async def contar_usuarios_por_perfil(self) -> Dict[int, int]:
        """Usuarios activos por cod_prf_usu, para mostrar en las tarjetas de rol."""
        rows = await self.execute(
            "SELECT cod_prf_usu, COUNT(*) AS total FROM usuarios "
            "WHERE cod_est_usu = 1 GROUP BY cod_prf_usu",
            None,
        )
        return {row["COD_PRF_USU"]: row["TOTAL"] for row in rows}

    async def contar_perfiles_taller(self) -> int:
        """Cuántos perfiles tiene el taller actual (RLS ya acota)."""
        row = await self.get_one("SELECT COUNT(*) AS total FROM perfiles", None)
        return row.get("TOTAL", 0) if row else 0

    async def buscar_por_nombre(self, nombre_prf: str, excluir_cod_prf: Optional[int] = None) -> Optional[Dict]:
        """Busca un perfil del taller actual por nombre, sin distinguir
        mayúsculas/minúsculas (para validar nombres únicos por taller)."""
        if excluir_cod_prf is not None:
            return await self.get_one(
                "SELECT cod_prf FROM perfiles WHERE LOWER(nombre_prf) = LOWER(:1) AND cod_prf != :2",
                (nombre_prf, excluir_cod_prf),
            )
        return await self.get_one(
            "SELECT cod_prf FROM perfiles WHERE LOWER(nombre_prf) = LOWER(:1)",
            (nombre_prf,),
        )

    async def contar_usuarios_de_perfil(self, cod_prf: int) -> int:
        """Cuántos usuarios (cualquier estado, activos o no) tiene asignado
        este perfil -- `usuarios` nunca se borra físicamente, así que un
        perfil con 0 usuarios activos puede igual tener inactivos cuyo FK
        rechazaría el DELETE; se cuentan todos para dar el mensaje amable
        antes de intentarlo."""
        row = await self.get_one(
            "SELECT COUNT(*) AS total FROM usuarios WHERE cod_prf_usu = :1", (cod_prf,)
        )
        return row.get("TOTAL", 0) if row else 0

    async def duplicar_perfil(
        self,
        nombre_prf: str,
        descripcion_prf: str,
        cod_prf_origen: int,
        usuario: str,
    ) -> int:
        """Crea un perfil nuevo (siempre no-admin) copiando los permisos de
        uno existente, en una sola transacción (perfil + permisos +
        auditoría, o nada)."""
        nuevo = await self.get_one("SELECT nextval('seq_perfiles') AS cod_prf", None)
        cod_prf = nuevo["COD_PRF"]
        statements = [
            (
                "INSERT INTO perfiles (cod_prf, nombre_prf, descripcion_prf, cod_est_prf, es_admin) "
                "VALUES (:1, :2, :3, 1, false)",
                (cod_prf, nombre_prf, descripcion_prf),
            ),
            (
                "INSERT INTO perfiles_permisos (cod_prm_pp, cod_prf_pp, cod_est_pp) "
                "SELECT cod_prm_pp, :1, cod_est_pp FROM perfiles_permisos "
                "WHERE cod_prf_pp = :2",
                (cod_prf, cod_prf_origen),
            ),
            (
                "INSERT INTO audit_log (cod_taller, usuario, tabla, evento, valor_nuevo) "
                "VALUES (current_setting('app.tenant_id')::integer, :1, 'perfiles', 'C', :2)",
                (
                    usuario,
                    Jsonb({
                        "cod_prf": cod_prf,
                        "nombre_prf": nombre_prf,
                        "duplicado_de": cod_prf_origen,
                    }),
                ),
            ),
        ]
        await self.execute_transaction(statements)
        return cod_prf

    async def eliminar_perfil(self, cod_prf: int, usuario: str) -> None:
        """Elimina un perfil y sus permisos en una sola transacción, con una
        entrada de auditoría. El caller ya validó que no tiene usuarios
        asignados y que no es el perfil Administrador."""
        statements = [
            (
                "DELETE FROM perfiles_permisos WHERE cod_prf_pp = :1",
                (cod_prf,),
            ),
            (
                "DELETE FROM perfiles WHERE cod_prf = :1",
                (cod_prf,),
            ),
            (
                "INSERT INTO audit_log (cod_taller, usuario, tabla, evento, valor_anterior) "
                "VALUES (current_setting('app.tenant_id')::integer, :1, 'perfiles', 'D', :2)",
                (usuario, Jsonb({"cod_prf": cod_prf})),
            ),
        ]
        await self.execute_transaction(statements)
