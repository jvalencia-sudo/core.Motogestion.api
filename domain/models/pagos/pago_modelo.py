from typing import Optional

from domain.models.base_model import BaseSchema


class PagoModelo(BaseSchema):
    cod_pago: int = 0
    cod_taller: int
    nombre_plan: str
    monto: int
    referencia: str
    estado: str = "PENDING"
    wompi_transaction_id: Optional[str] = None
