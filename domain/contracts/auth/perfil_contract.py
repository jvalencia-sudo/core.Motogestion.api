from typing import Optional
from pydantic import Field, field_validator

from domain.contracts.base_contract import BaseContractSchema


class CrearPerfilContract(BaseContractSchema):
    """Contrato para crear un nuevo perfil (rol propio del taller). No recibe
    es_admin: el servicio siempre crea perfiles nuevos como no-administrador
    -- un perfil nuevo nunca puede quedar con trato de administrador (F0-13 ext)."""
    nombre_prf: str = Field(..., min_length=1, max_length=100, description="Nombre del perfil")
    descripcion_prf: str = Field(..., min_length=1, max_length=255, description="Descripción del perfil")
    duplicar_de: Optional[int] = Field(
        None, gt=0, description="cod_prf de un perfil existente del taller del que copiar los permisos"
    )

    @field_validator("nombre_prf", "descripcion_prf")
    @classmethod
    def no_solo_espacios(cls, v):
        if v and not v.strip():
            raise ValueError("No puede contener solo espacios")
        return v.strip() if v else v


class ActualizarPerfilContract(BaseContractSchema):
    """Contrato para renombrar/editar un perfil existente. No recibe
    es_admin: no se puede retargetear un perfil hacia/desde Administrador
    por esta vía (F0-13 ext)."""
    cod_prf: int = Field(..., gt=0, description="Código del perfil a actualizar")
    nombre_prf: str = Field(..., min_length=1, max_length=100, description="Nombre del perfil")
    descripcion_prf: str = Field(..., min_length=1, max_length=255, description="Descripción del perfil")

    @field_validator("nombre_prf", "descripcion_prf")
    @classmethod
    def no_solo_espacios(cls, v):
        if v and not v.strip():
            raise ValueError("No puede contener solo espacios")
        return v.strip() if v else v


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
    es_admin: bool


class PerfilDetalleContract(BaseContractSchema):
    """Contrato de respuesta con detalles completos del perfil (vista)"""
    cod_prf: int
    nombre_prf: str
    descripcion_prf: str
    es_admin: bool
    cod_est_prf: Optional[int] = None
    nombre_est_prf: str
    num_usuarios: int = 0
