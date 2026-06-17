from typing import Optional
from pydantic import Field

from domain.contracts.base_contract import BaseContractSchema


class AsignarPermisoContract(BaseContractSchema):
    """Contrato para asignar un permiso a un perfil"""
    cod_prf: int = Field(..., description="Código del perfil")
    cod_rol: int = Field(..., description="Código del rol del perfil")
    cod_prm: int = Field(..., description="Código del permiso")
    cod_est: int = Field(default=1, description="Estado del permiso (1=activo, otro=inactivo)")


class CambiarEstadoPermisoContract(BaseContractSchema):
    """Contrato para activar/desactivar un permiso de un perfil"""
    cod_prf: int = Field(..., description="Código del perfil")
    cod_rol: int = Field(..., description="Código del rol del perfil")
    cod_prm: int = Field(..., description="Código del permiso")
    cod_est: int = Field(..., description="Estado del permiso (1=activo, otro=inactivo)")


class PermisoDisponibleContract(BaseContractSchema):
    """Contrato de respuesta para permisos disponibles"""
    cod_prm: int
    nombre_prm: str
    descripcion_prm: str
    ruta_vis_prm: str


class PermisoAsignadoContract(BaseContractSchema):
    """Contrato de respuesta para permisos asignados a un perfil"""
    cod_prf: int
    nombre_prf: str
    nombre_rol: str
    cod_prm: int
    nombre_prm: str
    descripcion_prm: str
    nombre_vis: str
    ruta_vis: str
    estado_permiso: str
