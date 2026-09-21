from typing import List

from fastapi import APIRouter

from domain.contracts.productos.producto_contract import ImpuestoResponseContract
from domain.services.productos.impuesto_servicio import ImpuestoServicio

router = APIRouter()


@router.get("", response_model=List[ImpuestoResponseContract])
async def listar_impuestos():
    """Catálogo de impuestos del taller (para asignarlos a productos)."""
    return await ImpuestoServicio().listar()
