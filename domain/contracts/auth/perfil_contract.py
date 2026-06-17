from typing import Optional
from pydantic import Field

from domain.contracts.base_contract import BaseContractSchema


class CrearPerfilContract(BaseContractSchema):
    """Contrato para crear un nuevo perfil"""
    nombre_prf: str = Field(..., min_length=1, max_length=100, description="Nombre del perfil")
    descripcion_prf: str = Field(..., min_length=1, max_length=255, description="Descripción del perfil")
    cod_rol_prf: int = Field(..., gt=0, description="Código del rol asociado al perfil")
    cod_est_prf: int = Field(default=1, description="Estado del perfil (1=activo, 2=inactivo)")


class ActualizarPerfilContract(BaseContractSchema):
    """Contrato para actualizar un perfil existente"""
    cod_prf: int = Field(..., gt=0, description="Código del perfil a actualizar")
    nombre_prf: str = Field(..., min_length=1, max_length=100, description="Nombre del perfil")
    descripcion_prf: str = Field(..., min_length=1, max_length=255, description="Descripción del perfil")
    cod_rol_prf: int = Field(..., gt=0, description="Código del rol asociado al perfil")


class CambiarEstadoPerfilContract(BaseContractSchema):
    """Contrato para activar/desactivar un perfil"""
    cod_prf: int = Field(..., gt=0, description="Código del perfil")
    cod_est_prf: int = Field(..., description="Estado del perfil (1=activo, 2=inactivo)")


class PerfilResponseContract(BaseContractSchema):
    """Contrato de respuesta para un perfil"""
    cod_prf: int
    nombre_prf: str
    descripcion_prf: str
    cod_est_prf: int
    cod_rol_prf: int


class PerfilDetalleContract(BaseContractSchema):
    """Contrato de respuesta con detalles completos del perfil (vista)"""
    cod_prf: int
    nombre_prf: str
    descripcion_prf: str
    nombre_est_prf: str
    nombre_rol_prf: str
