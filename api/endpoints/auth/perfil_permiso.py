from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException
from starlette.status import HTTP_200_OK, HTTP_201_CREATED

from domain.contracts.auth.perfil_permiso_contract import (
    AsignarPermisoContract,
    CambiarEstadoPermisoContract,
    PermisoDisponibleContract,
    PermisoAsignadoContract,
    ReemplazarPermisosContract,
)
from domain.contracts.shared.respuesta_contract import OperacionResponseContract
from domain.models.auth.perfil_permiso_modelo import VwPerfilesPermisosDetalle
from domain.services.auth.perfil_permiso_servicio import PerfilPermisoServicio
from infrastructure.dependencies.current_user import get_current_usuario

router = APIRouter()


@router.get("/todos", response_model=List[VwPerfilesPermisosDetalle])
async def obtener_todos_perfiles_permisos():
    """Obtiene todos los perfiles con sus permisos (vista completa)"""
    return await PerfilPermisoServicio().obtener_vw_perfiles_permisos_detalle()


@router.get("/perfil/{cod_prf}", response_model=List[PermisoAsignadoContract])
async def obtener_permisos_de_perfil(cod_prf: int):
    """Obtiene todos los permisos asignados a un perfil específico"""
    return await PerfilPermisoServicio().obtener_permisos_por_perfil(cod_prf)


@router.get("/perfil/{cod_prf}/disponibles", response_model=List[PermisoDisponibleContract])
async def obtener_permisos_disponibles(cod_prf: int):
    """Obtiene permisos que NO están asignados al perfil y pueden ser agregados"""
    return await PerfilPermisoServicio().obtener_permisos_disponibles(cod_prf)


@router.post("/asignar", status_code=HTTP_201_CREATED, response_model=OperacionResponseContract)
async def asignar_permiso(contract: AsignarPermisoContract):
    """Asigna un nuevo permiso a un perfil"""
    resultado = await PerfilPermisoServicio().asignar_permiso(contract)

    if not resultado.success:
        raise HTTPException(status_code=400, detail=resultado.message)

    return resultado


@router.put("/perfil/{cod_prf}/permisos", status_code=HTTP_200_OK, response_model=OperacionResponseContract)
async def reemplazar_permisos(
    cod_prf: int,
    contract: ReemplazarPermisosContract,
    current: Dict = Depends(get_current_usuario),
):
    """Reemplaza TODOS los permisos de un perfil de una vez (matriz de
    Usuarios y Roles, F0-13): la lista recibida es el estado final, no un
    delta. Transaccional (todo o nada) y queda en `audit_log`. `require_admin`
    ya se aplica a nivel de router (ver api/__init__.py), por eso solo se pide
    `get_current_usuario` acá -- es para saber QUIÉN hizo el cambio en la
    auditoría, no para autorizar."""
    return await PerfilPermisoServicio().reemplazar_permisos(
        cod_prf, contract, str(current.get("DOCUMENTO_USU")) if current else "desconocido"
    )


@router.put("/estado", status_code=HTTP_200_OK, response_model=OperacionResponseContract)
async def cambiar_estado_permiso(contract: CambiarEstadoPermisoContract):
    """Activa o desactiva un permiso de un perfil (no lo elimina, solo cambia el estado)"""
    resultado = await PerfilPermisoServicio().cambiar_estado_permiso(contract)

    if not resultado.success:
        raise HTTPException(status_code=400, detail=resultado.message)

    return resultado
