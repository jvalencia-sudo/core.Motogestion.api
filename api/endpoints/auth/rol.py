"""Catálogo de roles: solo lectura. F0-11 — este catálogo es global (sin cod_taller)
y se define en las migraciones de esquema, no desde la app; los POST/PUT/DELETE que
existían acá no tenían ningún control de acceso (cualquiera con un taller podía
renombrar "Administrador" para todos los talleres)."""
from typing import List

from fastapi import APIRouter

from domain.models.auth.rol_modelo import RolModelo
from domain.services.auth.rol_servicio import RolServicio

router = APIRouter()


@router.get("", response_model=List[RolModelo])
async def get():
    return await RolServicio().get_all()


@router.get("/{rol_id}", response_model=RolModelo)
async def get_customer_by_id(rol_id: int):
    return await RolServicio().get_by_id(rol_id)
