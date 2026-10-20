from datetime import datetime
from decimal import Decimal
from typing import Optional
from domain.models.base_model import BaseSchema


class PagoOrdenModelo(BaseSchema):
    cod_pago_orden: int = 0
    consecutivo_ot_pago: int
    valor_pago: Decimal
    metodo_pago: str
    documento_usu_pago: str
    referencia_pago: Optional[str] = None
    anulado_pago: bool = False
    motivo_anulacion_pago: Optional[str] = None
    fecha_anulacion_pago: Optional[datetime] = None
    documento_usu_anulacion_pago: Optional[str] = None


class VwPagosOrdenModelo(BaseSchema):
    cod_pago_orden: int
    consecutivo_ot_pago: int
    valor_pago: Decimal
    metodo_pago: str
    fecha_pago: datetime
    documento_usu_pago: str
    usuario_pago: str
    referencia_pago: Optional[str] = None
    anulado_pago: bool
    motivo_anulacion_pago: Optional[str] = None
    fecha_anulacion_pago: Optional[datetime] = None
    documento_usu_anulacion_pago: Optional[str] = None
