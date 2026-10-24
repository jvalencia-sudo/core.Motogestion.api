from datetime import datetime
from typing import Any, Dict, List, Optional
from domain.models.base_model import BaseSchema


class OrdenAprobacionCotizacionModelo(BaseSchema):
    """F2-03: fila de orden_aprobacion_cotizacion (aprobación vigente o
    histórica de una orden)."""
    consecutivo_ot: int
    aprobado_en: datetime
    ip: Optional[str] = None
    user_agent: Optional[str] = None
    items_snapshot: List[Dict[str, Any]]
    total_snapshot: float
    vigente: bool
