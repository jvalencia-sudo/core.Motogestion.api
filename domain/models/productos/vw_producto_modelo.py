from decimal import Decimal
from typing import Optional
from domain.models.base_model import BaseSchema


class VwProductoModelo(BaseSchema):
    """Modelo para la vista vw_productos"""
    cod_pro: int
    nombre_pro: str
    descripcion_pro: Optional[str] = None
    precio_pro: int
    stock_pro: Optional[Decimal] = None       # NULL para SERVICIO/PAQUETE
    stock_pro_min: Optional[Decimal] = None
    unidad_pro: str = "unidad"               # unidad | litro | galon | metro
    cod_est_pro: int
    estado_producto: Optional[str] = None
    tipo_pro: str = "BIEN"                 # BIEN | SERVICIO | PAQUETE
