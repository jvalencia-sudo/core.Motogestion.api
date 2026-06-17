from datetime import date, datetime
from typing import Optional
from domain.models.base_model import BaseSchema


class DetalleOrdenTrabajoModelo(BaseSchema):
    consecutivo_ot_deto: int
    cod_pro_deto: int
    fecha_confirmacion_deto: Optional[datetime] = None
    valor_unitario_deto: int
    cantidad_deto: int
    documento_usu_deto: str


class VwDetalleOtProductos(BaseSchema):
    consecutivo_ot_deto: int
    cod_pro_deto: int
    nombre_pro: str
    descripcion_pro: Optional[str] = None
    cantidad_deto: int
    valor_unitario_deto: int
    subtotal: float
    fecha_confirmacion_deto: Optional[datetime] = None
    usuario_confirmacion: str
    estado_producto: str
