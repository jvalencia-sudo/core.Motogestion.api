from decimal import Decimal
from typing import Optional
from domain.models.base_model import BaseSchema


class ProductoModelo(BaseSchema):
    cod_pro: int = 0
    nombre_pro: str
    descripcion_pro: Optional[str] = None
    # F1-03: NUMERIC(12,3) -- permite fracciones (p.ej. 1.5 litros de aceite).
    stock_pro: Optional[Decimal] = None       # NULL para SERVICIO/PAQUETE
    stock_pro_min: Optional[Decimal] = None
    cod_est_pro: int
    precio_pro: int
    tipo_pro: str = "BIEN"                 # BIEN | SERVICIO | PAQUETE
    unidad_pro: str = "unidad"              # unidad | litro | galon | metro
    dias_garantia_pro: int = 0              # F1-04: 0 = sin garantía


class VwProductosConImpuestos(BaseSchema):
    cod_pro: int
    nombre_pro: str
    descripcion_pro: Optional[str] = None
    precio_pro: int
    stock_pro: Decimal
    stock_pro_min: Decimal
    estado_producto: str
    cod_pro_imp: Optional[int] = None
    nombre_imp: Optional[str] = None
    porcentaje_pro_imp: Optional[float] = None
    valor_impuesto: Optional[float] = None
    precio_con_impuesto: Optional[float] = None


class VwInventarioAlertas(BaseSchema):
    cod_pro: int
    nombre_pro: str
    descripcion_pro: Optional[str] = None
    stock_pro: Decimal
    stock_pro_min: Decimal
    precio_pro: int
    estado: str
    nivel_alerta: str
    cantidad_a_pedir: Decimal
