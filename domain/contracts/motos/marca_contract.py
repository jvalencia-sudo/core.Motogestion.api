from typing import Optional
from pydantic import Field

from domain.contracts.base_contract import BaseContractSchema


class MarcaCreateContract(BaseContractSchema):
    """Contrato para crear una marca"""
    nombre_mar: str = Field(..., min_length=1, max_length=50, description="Nombre de la marca")


class MarcaUpdateContract(BaseContractSchema):
    """Contrato para actualizar una marca"""
    nombre_mar: Optional[str] = Field(None, min_length=1, max_length=50, description="Nombre de la marca")


class MarcaResponseContract(BaseContractSchema):
    """Contrato de respuesta para una marca"""
    cod_mar: int
    nombre_mar: str
