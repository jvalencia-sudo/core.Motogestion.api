from typing import Optional
from datetime import datetime
from decimal import Decimal
from pydantic import Field
from domain.contracts.base_contract import BaseContractSchema


class DetalleOrdenTrabajoContract(BaseContractSchema):
    """Contrato para agregar un producto a una orden de trabajo"""
    cod_pro_deto: int = Field(..., gt=0, description="Codigo del producto")
    # Decimal para permitir fracciones (p.ej. 1.5 h de mano de obra).
    cantidad_deto: Decimal = Field(..., ge=-99, le=99, description="Cantidad. Positivo: se factura, Negativo: no se factura (permite decimales)")
    valor_unitario_deto: Optional[int] = Field(None, gt=0, description="Valor unitario (si no se provee, se toma del producto)")


class DetalleOrdenTrabajoResponseContract(BaseContractSchema):
    """Contrato de respuesta para un detalle de orden de trabajo"""
    consecutivo_ot_deto: int
    cod_pro_deto: int
    nombre_pro: str
    descripcion_pro: Optional[str] = None
    cantidad_deto: Decimal
    valor_unitario_deto: int
    subtotal: float
    fecha_confirmacion_deto: Optional[datetime] = None
    usuario_confirmacion: str
    estado_producto: str


class DetalleOrdenUpdateContract(BaseContractSchema):
    """Contrato para actualizar cantidad de un producto en orden de trabajo"""
    cantidad_deto: Decimal = Field(..., ge=-99, le=99, description="Nueva cantidad. Positivo: se factura, Negativo: no se factura (permite decimales)")
