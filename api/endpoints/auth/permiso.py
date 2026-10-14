"""Catálogo de permisos: solo lectura. F0-11 — mismo motivo que rol.py: catálogo
global definido en migraciones, nunca gateado, sin control de acceso."""
from typing import List

from fastapi import APIRouter

from domain.models.auth.permiso_modelo import PermisoModelo, VwPermisoModelo
from domain.services.auth.permiso_servicio import PermisoServicio

router = APIRouter()


@router.get("", response_model=List[PermisoModelo])
async def get():
    return await PermisoServicio().get_all()


@router.get("/", response_model=List[VwPermisoModelo])
async def obtener_vw_permiso():
    return await PermisoServicio().obtener_vw_permisos()


@router.get("/{rol_id}", response_model=PermisoModelo)
async def get_customer_by_id(rol_id: int):
    return await PermisoServicio().get_by_id(rol_id)
