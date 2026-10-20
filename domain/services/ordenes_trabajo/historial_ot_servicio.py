from typing import List

from domain.contracts.ordenes_trabajo.orden_trabajo_contract import HistorialEventoContract
from repository.ordenes_trabajo.historial_ot_repositorio import HistorialOtRepositorio

EVENTO_LABELS = {"I": "Creado", "U": "Editado", "D": "Eliminado"}


class HistorialOtServicio:
    def __init__(self):
        self.repository = HistorialOtRepositorio()

    async def obtener_historial(self, consecutivo_ot: int) -> List[HistorialEventoContract]:
        """F1-05: historial de cambios de una orden (orden + su detalle),
        leído de audit_log. El dueño (Admin) puede ver el de cualquier orden."""
        filas = await self.repository.listar_por_orden(consecutivo_ot)
        return [
            HistorialEventoContract(
                fecha=f.get("FECHA"),
                usuario=f.get("USUARIO"),
                tabla=f.get("TABLA"),
                evento=EVENTO_LABELS.get(f.get("EVENTO"), f.get("EVENTO")),
                valor_anterior=f.get("VALOR_ANTERIOR"),
                valor_nuevo=f.get("VALOR_NUEVO"),
            )
            for f in filas
        ]
