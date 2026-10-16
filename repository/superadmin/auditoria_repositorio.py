from typing import Any, Dict, Optional

from psycopg.types.json import Jsonb

from repository.base_repository import BaseRepository


class AuditoriaRepositorio(BaseRepository):
    """Tabla `auditoria_superadmin` (SIN RLS -- el super-admin necesita verla
    completa, no aislada por tenant; ver infrastructure/utils/rls_policy.py)."""

    def __init__(self):
        super().__init__(schema="", table_name="auditoria_superadmin", primary_key="id", omit_key=True)

    def statement_registrar(
        self,
        usuario: str,
        cod_taller: Optional[int],
        accion: str,
        motivo: str,
        valor_anterior: Optional[Dict[str, Any]] = None,
        valor_nuevo: Optional[Dict[str, Any]] = None,
    ):
        """Devuelve el (query, params) para incluir como un statement más dentro del
        execute_transaction de la acción que la llama (mismo patrón de F0-13:
        perfiles_permisos + audit_log en una sola transacción)."""
        return (
            "INSERT INTO auditoria_superadmin "
            "(usuario, cod_taller, accion, valor_anterior, valor_nuevo, motivo) "
            "VALUES (:1, :2, :3, :4, :5, :6)",
            (
                usuario,
                cod_taller,
                accion,
                Jsonb(valor_anterior) if valor_anterior is not None else None,
                Jsonb(valor_nuevo) if valor_nuevo is not None else None,
                motivo,
            ),
        )

    async def listar_por_taller(self, cod_taller: int):
        return await self.db.execute(
            "SELECT usuario, to_char(fecha, 'YYYY-MM-DD HH24:MI') AS fecha, accion, "
            "valor_anterior, valor_nuevo, motivo "
            "FROM auditoria_superadmin WHERE cod_taller = :1 ORDER BY fecha DESC",
            (cod_taller,),
        )
