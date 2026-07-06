from typing import Dict, List, Optional

from fastapi import APIRouter, Depends
from starlette.status import HTTP_201_CREATED

from domain.models.inventario.inventario_model import (
    EntradaContract,
    MovimientoItem,
    ProductoStock,
    TomaFisicaContract,
)
from domain.services.inventario.inventario_servicio import InventarioServicio
from infrastructure.dependencies.current_user import get_current_usuario

router = APIRouter()


@router.get("/movimientos", response_model=List[MovimientoItem])
async def listar_movimientos(producto: Optional[int] = None):
    """Kardex de inventario (historial de movimientos). Acotado por RLS al taller."""
    return await InventarioServicio().listar_movimientos(producto)


@router.get("/productos", response_model=List[ProductoStock])
async def listar_productos():
    """Productos con su stock (para las pantallas de entrada y toma física)."""
    return await InventarioServicio().listar_productos()


@router.post("/entrada", status_code=HTTP_201_CREATED)
async def registrar_entrada(
    contract: EntradaContract,
    current: Optional[Dict] = Depends(get_current_usuario),
):
    """Registra una entrada de stock (reabastecimiento). Solo Admin/Recepcionista."""
    return await InventarioServicio().entrada(current, contract)


@router.post("/toma-fisica")
async def toma_fisica(
    contract: TomaFisicaContract,
    current: Optional[Dict] = Depends(get_current_usuario),
):
    """Aplica una toma física: ajusta el stock a las cantidades contadas y registra
    los movimientos AJUSTE. Solo Admin/Recepcionista."""
    return await InventarioServicio().toma_fisica(current, contract)
