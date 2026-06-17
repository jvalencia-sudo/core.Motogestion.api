from typing import Optional
from pydantic import Field, EmailStr

from domain.contracts.base_contract import BaseContractSchema


class ClienteCreateContract(BaseContractSchema):
    """Contrato para crear un cliente"""
    documento_cli: str = Field(..., min_length=8, max_length=11, description="Documento de identificación del cliente")
    nombre_cli: str = Field(..., min_length=1, max_length=50, description="Nombre del cliente")
    apellido_1_cli: str = Field(..., min_length=1, max_length=50, description="Primer apellido del cliente")
    apellido_2_cli: Optional[str] = Field(None, max_length=50, description="Segundo apellido del cliente")
    telefono_cli: str = Field(..., min_length=10, max_length=15, description="Teléfono del cliente")
    correo_cli: EmailStr = Field(..., description="Correo electrónico del cliente")
    direccion_cli: Optional[str] = Field(None, max_length=500, description="Dirección del cliente")


class ClienteUpdateContract(BaseContractSchema):
    """Contrato para actualizar un cliente (documento_cli no es actualizable)"""
    nombre_cli: Optional[str] = Field(None, min_length=1, max_length=50, description="Nombre del cliente")
    apellido_1_cli: Optional[str] = Field(None, min_length=1, max_length=50, description="Primer apellido del cliente")
    apellido_2_cli: Optional[str] = Field(None, max_length=50, description="Segundo apellido del cliente")
    telefono_cli: Optional[str] = Field(None, min_length=10, max_length=15, description="Teléfono del cliente")
    correo_cli: Optional[EmailStr] = Field(None, description="Correo electrónico del cliente")
    direccion_cli: Optional[str] = Field(None, max_length=500, description="Dirección del cliente")


class ClienteResponseContract(BaseContractSchema):
    """Contrato de respuesta para un cliente"""
    documento_cli: str
    nombre_completo: str
    telefono_cli: str
    correo_cli: str
    direccion_cli: Optional[str] = None
    total_motos: int
