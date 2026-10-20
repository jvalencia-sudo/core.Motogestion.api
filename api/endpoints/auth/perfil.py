from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException
from starlette.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_204_NO_CONTENT

from domain.contracts.auth.perfil_contract import (
    CrearPerfilContract,
    ActualizarPerfilContract,
    CambiarEstadoPerfilContract,
    PerfilResponseContract,
    PerfilDetalleContract
)
from domain.contracts.shared.respuesta_contract import (
    OperacionResponseContract,
    PerfilCreadoResponseContract,
)
from domain.services.auth.perfil_servicio import PerfilServicio
from infrastructure.dependencies.current_user import get_current_usuario

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


@router.post("", status_code=HTTP_201_CREATED, response_model=PerfilCreadoResponseContract)
async def crear_perfil(contract: CrearPerfilContract, current: Dict = Depends(get_current_usuario)):
    """Crea un nuevo perfil propio del taller (desde cero o duplicando otro)"""
    return await PerfilServicio().crear_perfil(
        contract, str(current.get("DOCUMENTO_USU")) if current else "desconocido"
    )


@router.put("/estado", status_code=HTTP_200_OK, response_model=OperacionResponseContract)
async def cambiar_estado_perfil(contract: CambiarEstadoPerfilContract):
    """Activa o desactiva un perfil (no lo elimina, solo cambia el estado)"""
    resultado = await PerfilServicio().cambiar_estado_perfil(contract)

    if not resultado["success"]:
        raise HTTPException(status_code=404, detail=resultado["message"])

    return resultado


@router.put("", status_code=HTTP_200_OK, response_model=OperacionResponseContract)
async def actualizar_perfil(contract: ActualizarPerfilContract):
    """Renombra/edita un perfil existente"""
    return await PerfilServicio().actualizar_perfil(contract)


@router.get("/{cod_prf}", response_model=PerfilResponseContract)
async def obtener_perfil_por_id(cod_prf: int):
    """Obtiene un perfil específico por su código"""
    perfil = await PerfilServicio().get_by_id(cod_prf)
    if not perfil:
        raise HTTPException(status_code=404, detail="Perfil no encontrado")
    return perfil


@router.delete("/{cod_prf}", status_code=HTTP_204_NO_CONTENT)
async def eliminar_perfil(cod_prf: int, current: Dict = Depends(get_current_usuario)):
    """Elimina un perfil propio del taller (nunca el Administrador, nunca con usuarios asignados)"""
    await PerfilServicio().eliminar_perfil(
        cod_prf, str(current.get("DOCUMENTO_USU")) if current else "desconocido"
    )
    return None


