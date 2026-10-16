from pydantic import Field

from domain.contracts.base_contract import BaseContractSchema


class ExtenderPruebaContract(BaseContractSchema):
    dias: int = Field(..., gt=0)
    motivo: str = Field(..., min_length=1)


class PagoManualContract(BaseContractSchema):
    monto: int = Field(..., gt=0)
    detalle_medio: str = Field(..., min_length=1, description="Efectivo/Transferencia/Nequi")
    nombre_plan: str = Field(default="Taller")
    motivo: str = Field(..., min_length=1)


class SuspenderReactivarContract(BaseContractSchema):
    motivo: str = Field(..., min_length=1)


class AjustarPrecioContract(BaseContractSchema):
    precio_susc_tal: int = Field(..., ge=0)
    motivo: str = Field(..., min_length=1)
