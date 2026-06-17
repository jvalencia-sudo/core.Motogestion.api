from typing import Optional
from pydantic import Field

from domain.contracts.base_contract import BaseContractSchema


class MotoCreateContract(BaseContractSchema):
    """Contrato para crear una moto"""
    placa_mot: str = Field(..., min_length=5, max_length=6, description="Placa de la moto (5-6 caracteres)")
    modelo_mot: int = Field(..., ge=1900, le=2100, description="Año modelo de la moto")
    color_mot: str = Field(..., min_length=1, max_length=50, description="Color de la moto")
    cilindraje_mot: int = Field(..., gt=0, description="Cilindraje de la moto (debe ser mayor a 0)")
    documento_cli_mot: str = Field(..., min_length=8, max_length=11, description="Documento del propietario")
    cod_marca_mot: int = Field(..., gt=0, description="Código de la marca (debe ser mayor a 0)")


class MotoUpdateContract(BaseContractSchema):
    """Contrato para actualizar una moto"""
    placa_mot: Optional[str] = Field(None, min_length=5, max_length=6, description="Placa de la moto")
    modelo_mot: Optional[int] = Field(None, ge=1900, le=2100, description="Año modelo de la moto")
    color_mot: Optional[str] = Field(None, min_length=1, max_length=50, description="Color de la moto")
    cilindraje_mot: Optional[int] = Field(None, gt=0, description="Cilindraje de la moto")
    documento_cli_mot: Optional[str] = Field(None, min_length=8, max_length=11, description="Documento del propietario")
    cod_marca_mot: Optional[int] = Field(None, gt=0, description="Código de la marca")


class MotoResponseContract(BaseContractSchema):
    """Contrato de respuesta para una moto"""
    placa_mot: str
    modelo_mot: int
    color_mot: str
    cilindraje_mot: int
    marca: str
    propietario: str
    telefono_cli: str
    total_ordenes: int


class MotoClienteResponseContract(BaseContractSchema):
    """Contrato de respuesta para motos de un cliente (con información de marca)"""
    placa_mot: str
    modelo_mot: int
    color_mot: str
    cilindraje_mot: int
    documento_cli_mot: str
    cod_marca_mot: int
    nombre_marca: str
