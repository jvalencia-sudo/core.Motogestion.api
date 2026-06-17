from typing import Dict, List
from fastapi import APIRouter, Query
from starlette.status import HTTP_200_OK, HTTP_201_CREATED

from domain.contracts.admin.admin_user_contract import (
    AdminUserCreationContract,
    AdminUserUpdateContract,
    ChangePasswordContract,
    UserFilterContract,
    UpdateUserProfileContract
)
from domain.models.auth.user_model import UserModel, VwUsuariosPerfiles
from domain.services.admin.admin_user_service import AdminUserService

router = APIRouter()


@router.post("", status_code=HTTP_201_CREATED, response_model=UserModel)
async def create_user(contract: AdminUserCreationContract):
    """
    Crea un nuevo usuario con contraseña en Auth0 y BD.

    - **documento_usu**: Documento de identidad único
    - **nombre_usu**: Nombre del usuario
    - **apellido_1_usu**: Primer apellido
    - **apellido_2_usu**: Segundo apellido (opcional)
    - **correo_usu**: Email único
    - **password**: Contraseña (mínimo 8 caracteres)
    - **cod_prf_usu**: ID del perfil
    - **cod_rol_prf_usu**: ID del rol
    - **cod_tipo_usu**: Tipo de usuario (1=cliente, 2=admin, etc.)
    - **cod_est_usu**: Estado (1=activo, 0=inactivo)
    """
    return await AdminUserService().create_user_with_password(contract)


@router.get("", status_code=HTTP_200_OK)
async def list_users(
    nombre: str = Query(None, description="Buscar por nombre o apellido"),
    correo: str = Query(None, description="Buscar por correo"),
    documento_usu: str = Query(None, description="Buscar por documento"),
    cod_est_usu: int = Query(None, description="Filtrar por estado (1=activo, 0=inactivo)"),
    cod_prf_usu: int = Query(None, description="Filtrar por perfil"),
    cod_rol_prf_usu: int = Query(None, description="Filtrar por rol"),
    cod_tipo_usu: int = Query(None, description="Filtrar por tipo de usuario"),
    limit: int = Query(50, ge=1, le=500, description="Límite de resultados"),
    offset: int = Query(0, ge=0, description="Offset para paginación")
):
    """
    Lista usuarios con filtros y paginación.

    Retorna un objeto con:
    - **users**: Lista de usuarios
    - **total**: Total de usuarios que coinciden con los filtros
    - **limit**: Límite usado
    - **offset**: Offset usado
    - **total_pages**: Total de páginas
    """
    filters = UserFilterContract(
        nombre=nombre,
        correo=correo,
        documento_usu=documento_usu,
        cod_est_usu=cod_est_usu,
        cod_prf_usu=cod_prf_usu,
        cod_rol_prf_usu=cod_rol_prf_usu,
        cod_tipo_usu=cod_tipo_usu,
        limit=limit,
        offset=offset
    )
    return await AdminUserService().list_users_with_filters(filters)


@router.get("/all", status_code=HTTP_200_OK, response_model=List[VwUsuariosPerfiles])
async def get_usuarios_perfiles():
    """
    Obtiene todos los usuarios con información completa de perfiles y roles.

    Retorna los datos de la vista vw_usuarios_perfiles que incluye:
    - **documento_usu**: Documento del usuario
    - **nombre_completo**: Nombre completo del usuario
    - **correo_usu**: Email del usuario
    - **cod_tipo_usu**: Código de tipo de usuario
    - **estado_usuario**: Nombre del estado del usuario
    - **perfil**: Nombre del perfil
    - **descripcion_perfil**: Descripción del perfil
    - **rol**: Nombre del rol
    - **descripcion_rol**: Descripción del rol
    """
    return await AdminUserService().get_usuarios_perfiles()


@router.get("/perfiles/{documento}", status_code=HTTP_200_OK, response_model=VwUsuariosPerfiles)
async def get_usuario_perfil(documento: str):
    """
    Obtiene un usuario específico con información completa de perfil y rol.

    Retorna los datos de la vista vw_usuarios_perfiles para un usuario específico.
    """
    return await AdminUserService().get_usuario_perfil_by_documento(documento)


@router.get("/{documento_usu}", status_code=HTTP_200_OK, response_model=UserModel)
async def get_user(documento_usu: str):
    """
    Obtiene un usuario específico por su documento.
    """
    return await AdminUserService().get_user_by_documento(documento_usu)


@router.put("/{documento_usu}", status_code=HTTP_200_OK, response_model=UserModel)
async def update_user(documento_usu: str, contract: AdminUserUpdateContract):
    """
    Actualiza los datos de un usuario.

    Solo los campos proporcionados serán actualizados.
    Si se actualiza el email, también se actualiza en Auth0.
    """
    return await AdminUserService().update_user_admin(documento_usu, contract)


@router.delete("/{documento_usu}", status_code=HTTP_200_OK)
async def deactivate_user(documento_usu: str) -> Dict[str, str]:
    """
    Desactiva un usuario (soft delete).

    El usuario se marca como inactivo (cod_est_usu = 0) pero no se elimina de la BD.
    """
    return await AdminUserService().deactivate_user(documento_usu)


@router.post("/{documento_usu}/activate", status_code=HTTP_200_OK)
async def activate_user(documento_usu: str) -> Dict[str, str]:
    """
    Activa un usuario previamente desactivado.

    Cambia el estado a activo (cod_est_usu = 1).
    """
    return await AdminUserService().activate_user(documento_usu)


@router.post("/{documento_usu}/reset-password", status_code=HTTP_200_OK)
async def reset_password(documento_usu: str, contract: ChangePasswordContract) -> Dict[str, str]:
    """
    Resetea la contraseña de un usuario en Auth0.

    - **new_password**: Nueva contraseña (mínimo 8 caracteres)
    """
    return await AdminUserService().reset_user_password(documento_usu, contract)


@router.put("/{documento_usu}/profile", status_code=HTTP_200_OK, response_model=UserModel)
async def update_user_profile(documento_usu: str, contract: UpdateUserProfileContract):
    """
    Actualiza el perfil y rol de un usuario (cambia sus permisos).

    - **cod_prf_usu**: Nuevo código de perfil
    - **cod_rol_prf_usu**: Nuevo código de rol
    """
    return await AdminUserService().update_user_profile(documento_usu, contract)
