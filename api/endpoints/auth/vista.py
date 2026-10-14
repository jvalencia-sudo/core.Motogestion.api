"""Catálogo de vistas: solo lectura. F0-11 — mismo motivo que rol.py: catálogo
global definido en migraciones, nunca gateado, sin control de acceso."""
from typing import List

from fastapi import APIRouter

from domain.models.auth.vista_modelo import VistaModelo
from domain.services.auth.vista_servicio import VistaServicio

router = APIRouter()


@router.get("", response_model=List[VistaModelo])
async def get():
    return await VistaServicio().get_all()


@router.get("/{rol_id}", response_model=VistaModelo)
async def get_customer_by_id(rol_id: int):
    return await VistaServicio().get_by_id(rol_id)
