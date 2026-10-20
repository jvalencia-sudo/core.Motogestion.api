from typing import Dict, List

from repository.base_repository import BaseRepository


class HistorialOtRepositorio(BaseRepository):
    """F1-05: lee el historial de cambios de una orden desde `audit_log` --
    une los eventos de la orden misma y los de su detalle (líneas de
    productos/servicios). Tabla ya auditada por los triggers tg_audit_*,
    aquí solo se LEE."""

    def __init__(self):
        super().__init__(schema="", table_name="audit_log", primary_key="id", omit_key=True)

    async def listar_por_orden(self, consecutivo_ot: int) -> List[Dict]:
        query = (
            "SELECT fecha, usuario, tabla, evento, valor_anterior, valor_nuevo "
            "FROM audit_log "
            "WHERE (tabla = 'ordenes_trabajo' "
            "       AND (COALESCE(valor_nuevo, valor_anterior)->>'consecutivo_ot')::int = :1) "
            "   OR (tabla = 'detalle_orden_trabajo' "
            "       AND (COALESCE(valor_nuevo, valor_anterior)->>'consecutivo_ot_deto')::int = :2) "
            "ORDER BY fecha DESC, id DESC"
        )
        # cada :N es un placeholder posicional independiente (no un bind con nombre
        # reutilizable como en Oracle) -- ver _translate en repository/data/database.py.
        return await self.execute(query, (consecutivo_ot, consecutivo_ot))
