from typing import List

from fastapi import APIRouter, HTTPException, Query
from starlette.status import HTTP_200_OK, HTTP_201_CREATED

from domain.contracts.auth.perfil_permiso_contract import (
    AsignarPermisoContract,
    CambiarEstadoPermisoContract,
    PermisoDisponibleContract,
    PermisoAsignadoContract
)
from domain.models.auth.perfil_permiso_modelo import VwPerfilesPermisosDetalle
from domain.services.auth.perfil_permiso_servicio import PerfilPermisoServicio

router = APIRouter()


@router.get("/todos", response_model=List[VwPerfilesPermisosDetalle])
async def obtener_todos_perfiles_permisos():
    """Obtiene todos los perfiles con sus permisos (vista completa)"""
    return await PerfilPermisoServicio().obtener_vw_perfiles_permisos_detalle()


@router.get("/perfil/{cod_prf}", response_model=List[PermisoAsignadoContract])
async def obtener_permisos_de_perfil(
    cod_prf: int,
    cod_rol: int = Query(..., description="Código del rol del perfil")
):
    """Obtiene todos los permisos asignados a un perfil específico"""
    return await PerfilPermisoServicio().obtener_permisos_por_perfil(cod_prf, cod_rol)


@router.get("/perfil/{cod_prf}/disponibles", response_model=List[PermisoDisponibleContract])
async def obtener_permisos_disponibles(
    cod_prf: int,
    cod_rol: int = Query(..., description="Código del rol del perfil")
):
    """Obtiene permisos que NO están asignados al perfil y pueden ser agregados"""
    return await PerfilPermisoServicio().obtener_permisos_disponibles(cod_prf, cod_rol)


@router.post("/asignar", status_code=HTTP_201_CREATED)
async def asignar_permiso(contract: AsignarPermisoContract):
    """Asigna un nuevo permiso a un perfil"""
    resultado = await PerfilPermisoServicio().asignar_permiso(contract)

    if not resultado["success"]:
        raise HTTPException(status_code=400, detail=resultado["message"])

    return resultado


@router.put("/estado", status_code=HTTP_200_OK)
async def cambiar_estado_permiso(contract: CambiarEstadoPermisoContract):
    """Activa o desactiva un permiso de un perfil (no lo elimina, solo cambia el estado)"""
    resultado = await PerfilPermisoServicio().cambiar_estado_permiso(contract)

    if not resultado["success"]:
        raise HTTPException(status_code=400, detail=resultado["message"])

    return resultado
