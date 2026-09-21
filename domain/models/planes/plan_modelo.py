from typing import Dict, Optional

from domain.models.base_model import BaseSchema


class PlanModelo(BaseSchema):
    cod_plan: int = 0
    nombre_plan: str
    precio_plan: int = 0
    max_usuarios: Optional[int] = None   # NULL = ilimitado
    max_motos: Optional[int] = None
    features: Dict = {}
    orden: int = 0
