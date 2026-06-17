from typing import Optional
from domain.models.base_model import BaseSchema


class ProductoModelo(BaseSchema):
    cod_pro: int = 0
    nombre_pro: str
    descripcion_pro: Optional[str] = None
    stock_pro: int
    stock_pro_min: int
    cod_est_pro: int
    precio_pro: int


class VwProductosConImpuestos(BaseSchema):
    cod_pro: int
    nombre_pro: str
    descripcion_pro: Optional[str] = None
    precio_pro: int
    stock_pro: int
    stock_pro_min: int
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
    stock_pro: int
    stock_pro_min: int
    precio_pro: int
    estado: str
    nivel_alerta: str
    cantidad_a_pedir: int
