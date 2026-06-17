from typing import Optional
from pydantic import EmailStr, Field
from domain.models.base_model import BaseSchema


class AdminUserCreationContract(BaseSchema):
    """Contrato para crear un usuario desde el panel de administrador"""
    documento_usu: str = Field(..., description="Documento de identidad del usuario")
    nombre_usu: str = Field(..., description="Nombre del usuario")
    apellido_1_usu: str = Field(..., description="Primer apellido")
    apellido_2_usu: Optional[str] = Field(None, description="Segundo apellido")
    correo_usu: EmailStr = Field(..., description="Correo electrónico")
    password: str = Field(..., min_length=8, description="Contraseña (mínimo 8 caracteres)")
    cod_prf_usu: int = Field(..., description="Código del perfil")
    cod_rol_prf_usu: int = Field(..., description="Código del rol del perfil")
    cod_tipo_usu: Optional[int] = Field(1, description="Tipo de usuario (1=cliente, 2=admin, etc)")
    cod_est_usu: Optional[int] = Field(1, description="Estado del usuario (1=activo, 0=inactivo)")


class AdminUserUpdateContract(BaseSchema):
    """Contrato para actualizar un usuario desde el panel de administrador"""
    documento_usu: Optional[str] = Field(None, description="Documento de identidad del usuario")
    nombre_usu: Optional[str] = Field(None, description="Nombre del usuario")
    apellido_1_usu: Optional[str] = Field(None, description="Primer apellido")
    apellido_2_usu: Optional[str] = Field(None, description="Segundo apellido")
    correo_usu: Optional[EmailStr] = Field(None, description="Correo electrónico")
    cod_prf_usu: Optional[int] = Field(None, description="Código del perfil")
    cod_rol_prf_usu: Optional[int] = Field(None, description="Código del rol del perfil")
    cod_tipo_usu: Optional[int] = Field(None, description="Tipo de usuario")
    cod_est_usu: Optional[int] = Field(None, description="Estado del usuario")


class ChangePasswordContract(BaseSchema):
    """Contrato para cambiar/resetear la contraseña de un usuario"""
    new_password: str = Field(..., min_length=8, description="Nueva contraseña (mínimo 8 caracteres)")


class UserFilterContract(BaseSchema):
    """Contrato para filtrar usuarios en el listado"""
    nombre: Optional[str] = Field(None, description="Buscar por nombre o apellido")
    correo: Optional[str] = Field(None, description="Buscar por correo electrónico")
    cod_est_usu: Optional[int] = Field(None, description="Filtrar por estado (1=activo, 0=inactivo)")
    cod_prf_usu: Optional[int] = Field(None, description="Filtrar por perfil")
    cod_rol_prf_usu: Optional[int] = Field(None, description="Filtrar por rol")
    cod_tipo_usu: Optional[int] = Field(None, description="Filtrar por tipo de usuario")
    documento_usu: Optional[str] = Field(None, description="Buscar por documento")
    limit: Optional[int] = Field(50, description="Límite de resultados", ge=1, le=500)
    offset: Optional[int] = Field(0, description="Offset para paginación", ge=0)


class UpdateUserProfileContract(BaseSchema):
    """Contrato para actualizar el perfil y rol de un usuario"""
    cod_prf_usu: int = Field(..., description="Código del perfil")
    cod_rol_prf_usu: int = Field(..., description="Código del rol del perfil")
