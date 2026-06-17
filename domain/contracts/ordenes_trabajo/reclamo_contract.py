from typing import Optional
from datetime import date
from pydantic import Field, field_validator
from domain.contracts.base_contract import BaseContractSchema


class ReclamoCreateContract(BaseContractSchema):
    """Contrato para crear un reclamo"""
    descripcion_rec: str = Field(..., min_length=5, max_length=500, description="Descripción del reclamo")
    consecutivo_ot_rec: int = Field(..., gt=0, description="Consecutivo de la orden de trabajo")

    @field_validator('descripcion_rec')
    @classmethod
    def validar_descripcion(cls, v):
        """Valida que la descripción no sea solo espacios"""
        if v and not v.strip():
            raise ValueError('La descripción no puede contener solo espacios')
        return v.strip() if v else v


class ReclamoUpdateContract(BaseContractSchema):
    """Contrato para actualizar un reclamo"""
    descripcion_rec: Optional[str] = Field(None, min_length=5, max_length=500, description="Descripción del reclamo")

    @field_validator('descripcion_rec')
    @classmethod
    def validar_descripcion(cls, v):
        """Valida que la descripción no sea solo espacios"""
        if v and not v.strip():
            raise ValueError('La descripción no puede contener solo espacios')
        return v.strip() if v else v


class ReclamoResponseContract(BaseContractSchema):
    """Contrato de respuesta para un reclamo completo"""
    cod_rec: int
    descripcion_rec: str
    consecutivo_ot_rec: int

    # Información de la OT
    fecha_elaboracion_ot: date
    fecha_entrega_ot: Optional[date] = None
    kilometraje_ingreso_ot: int
    observacion_cli_ot: Optional[str] = None
    observacion_ot: Optional[str] = None
    fecha_fin_garantia_ot: Optional[date] = None
    estado_ot: str

    # Información de la moto
    placa_mot: str
    modelo_mot: int
    color_mot: str
    cilindraje_mot: int
    marca_moto: str
    moto_completa: str

    # Información del cliente
    documento_cli: str
    nombre_completo_cliente: str
    telefono_cli: str
    correo_cli: str
    direccion_cli: Optional[str] = None

    # Información de usuarios responsables
    documento_recepcionista: str
    recepcionista: str
    documento_mecanico: str
    mecanico: str

    # Información de garantía
    estado_garantia: str
    dias_garantia_restantes: Optional[int] = None


class ReclamoResumenContract(BaseContractSchema):
    """Contrato de respuesta resumida para listados de reclamos"""
    cod_rec: int
    descripcion_rec: str
    consecutivo_ot_rec: int
    placa_mot: str
    nombre_completo_cliente: str
    telefono_cli: str
    estado_ot: str
    fecha_elaboracion_ot: date
    estado_garantia: str
