from typing import Literal, Optional
from datetime import datetime
from decimal import Decimal
from pydantic import Field, field_validator
from domain.contracts.base_contract import BaseContractSchema

MetodoPago = Literal["EFECTIVO", "TRANSFERENCIA", "NEQUI", "DAVIPLATA", "TARJETA", "OTRO"]


class PagoOrdenCreateContract(BaseContractSchema):
    """F1-07: registra un abono/pago de un cliente a una orden. Los pagos no
    se editan ni se borran -- solo se anulan con motivo (ver AnularPagoContract)."""
    valor_pago: Decimal = Field(..., gt=0, description="Valor del abono (siempre positivo)")
    metodo_pago: MetodoPago = Field(..., description="Método de pago")
    referencia_pago: Optional[str] = Field(None, max_length=80, description="Referencia (ej. número de transferencia)")


class AnularPagoContract(BaseContractSchema):
    """Motivo obligatorio para anular un pago -- igual que anular una orden (F1-05)."""
    motivo: str = Field(..., min_length=5, max_length=500, description="Motivo de la anulación")

    @field_validator('motivo')
    @classmethod
    def no_solo_espacios(cls, v):
        if not v.strip():
            raise ValueError("El motivo no puede estar vacío")
        return v.strip()


class PagoOrdenResponseContract(BaseContractSchema):
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
