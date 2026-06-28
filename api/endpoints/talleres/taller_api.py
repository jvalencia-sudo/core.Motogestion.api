from typing import List

from fastapi import APIRouter, Depends, status

from domain.contracts.talleres.taller_contract import (
    TallerRegistroContract,
    TallerRegistroResponse,
    TallerUpdateContract,
)
from domain.models.talleres.taller_model import TallerModel
from domain.services.talleres.taller_servicio import TallerServicio
from infrastructure.dependencies.current_user import require_super_admin

router = APIRouter()


@router.post("", response_model=TallerRegistroResponse, status_code=status.HTTP_201_CREATED)
async def registrar_taller(contract: TallerRegistroContract):
    """
    Registra un taller nuevo (endpoint público para la landing).

    Crea el taller, su usuario dueño (pre-registrado por correo) y catálogos base.
    El dueño inicia sesión luego con ese correo (el login es cerrado a usuarios registrados).
    """
    return await TallerServicio().registrar(contract)


# Endpoints de gestión: solo super-admin (Admin del taller plataforma) puede
# listar/ver/editar TODOS los talleres.

@router.get("", response_model=List[TallerModel], dependencies=[Depends(require_super_admin)])
async def listar_talleres():
    """Lista todos los talleres (vista de gestión / super-admin)."""
    return await TallerServicio().listar()


@router.get("/{cod_taller}", response_model=TallerModel, dependencies=[Depends(require_super_admin)])
async def obtener_taller(cod_taller: int):
    """Obtiene un taller por su código."""
    return await TallerServicio().obtener(cod_taller)


@router.put("/{cod_taller}", response_model=TallerModel, dependencies=[Depends(require_super_admin)])
async def actualizar_taller(cod_taller: int, contract: TallerUpdateContract):
    """Actualiza los datos / estado / plan de un taller."""
    return await TallerServicio().actualizar(cod_taller, contract)
