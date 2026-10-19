from typing import Optional
from datetime import datetime
from decimal import Decimal
from pydantic import Field, model_validator
from domain.contracts.base_contract import BaseContractSchema


class DetalleOrdenTrabajoContract(BaseContractSchema):
    """Contrato para agregar un producto a una orden de trabajo"""
    cod_pro_deto: int = Field(..., gt=0, description="Codigo del producto")
    # Decimal para permitir fracciones (p.ej. 1.5 h de mano de obra o 1.5 litros).
    cantidad_deto: Decimal = Field(..., gt=0, description="Cantidad (siempre positiva; permite decimales)")
    valor_unitario_deto: Optional[int] = Field(None, gt=0, description="Valor unitario (si no se provee, se toma del producto)")
    cobrar_deto: bool = Field(True, description="Si es false: no se factura, pero SÍ descuenta stock (cortesía)")
    motivo_no_cobro_deto: Optional[str] = Field(None, max_length=200, description="Obligatorio si cobrar_deto es false")

    @model_validator(mode="after")
    def _motivo_obligatorio_si_no_cobra(self):
        if not self.cobrar_deto and not (self.motivo_no_cobro_deto and self.motivo_no_cobro_deto.strip()):
            raise ValueError("motivo_no_cobro_deto es obligatorio cuando cobrar_deto es false")
        return self


class DetalleOrdenTrabajoResponseContract(BaseContractSchema):
    """Contrato de respuesta para un detalle de orden de trabajo"""
    consecutivo_ot_deto: int
    cod_pro_deto: int
    nombre_pro: str
    descripcion_pro: Optional[str] = None
    cantidad_deto: Decimal
    valor_unitario_deto: int
    cobrar_deto: bool
    motivo_no_cobro_deto: Optional[str] = None
    subtotal: float
    fecha_confirmacion_deto: Optional[datetime] = None
    usuario_confirmacion: str
    estado_producto: str


class DetalleOrdenUpdateContract(BaseContractSchema):
    """Contrato para actualizar cantidad de un producto en orden de trabajo"""
    cantidad_deto: Decimal = Field(..., gt=0, description="Nueva cantidad (siempre positiva; permite decimales)")
    cobrar_deto: bool = Field(True, description="Si es false: no se factura, pero SÍ descuenta stock (cortesía)")
    motivo_no_cobro_deto: Optional[str] = Field(None, max_length=200, description="Obligatorio si cobrar_deto es false")

    @model_validator(mode="after")
    def _motivo_obligatorio_si_no_cobra(self):
        if not self.cobrar_deto and not (self.motivo_no_cobro_deto and self.motivo_no_cobro_deto.strip()):
            raise ValueError("motivo_no_cobro_deto es obligatorio cuando cobrar_deto es false")
        return self
