from typing import List

from fastapi import APIRouter, HTTPException
from starlette.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_204_NO_CONTENT

from domain.contracts.auth.perfil_contract import (
    CrearPerfilContract,
    ActualizarPerfilContract,
    CambiarEstadoPerfilContract,
    PerfilResponseContract,
    PerfilDetalleContract
)
from domain.services.auth.perfil_servicio import PerfilServicio

router = APIRouter()


# IMPORTANTE: Las rutas específicas (/todos, /estado) deben ir ANTES de las rutas con parámetros (/{cod_prf})
# para evitar conflictos de matching


@router.get("", response_model=List[PerfilResponseContract])
async def obtener_perfiles():
    """Obtiene todos los perfiles (datos básicos de la tabla)"""
    return await PerfilServicio().get_all()


@router.get("/todos", response_model=List[PerfilDetalleContract])
async def obtener_todos_perfiles():
    """Obtiene todos los perfiles con información completa (vista)"""
    return await PerfilServicio().obtener_vw_perfiles()


@router.post("", status_code=HTTP_201_CREATED)
async def crear_perfil(contract: CrearPerfilContract):
    """Crea un nuevo perfil"""
    resultado = await PerfilServicio().crear_perfil(contract)

    if not resultado["success"]:
        raise HTTPException(status_code=400, detail=resultado["message"])

    return resultado


@router.put("/estado", status_code=HTTP_200_OK)
async def cambiar_estado_perfil(contract: CambiarEstadoPerfilContract):
    """Activa o desactiva un perfil (no lo elimina, solo cambia el estado)"""
    resultado = await PerfilServicio().cambiar_estado_perfil(contract)

    if not resultado["success"]:
        raise HTTPException(status_code=404, detail=resultado["message"])

    return resultado


@router.put("", status_code=HTTP_200_OK)
async def actualizar_perfil(contract: ActualizarPerfilContract):
    """Actualiza un perfil existente"""
    resultado = await PerfilServicio().actualizar_perfil(contract)

    if not resultado["success"]:
        raise HTTPException(status_code=404, detail=resultado["message"])

    return resultado


@router.get("/{cod_prf}", response_model=PerfilResponseContract)
async def obtener_perfil_por_id(cod_prf: int):
    """Obtiene un perfil específico por su código"""
    perfil = await PerfilServicio().get_by_id(cod_prf)
    if not perfil:
        raise HTTPException(status_code=404, detail="Perfil no encontrado")
    return perfil


@router.delete("/{cod_prf}", status_code=HTTP_204_NO_CONTENT)
async def eliminar_perfil(cod_prf: int):
    """Elimina físicamente un perfil de la base de datos"""
    await PerfilServicio().delete(cod_prf)
    return None


