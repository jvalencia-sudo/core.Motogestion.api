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
from infrastructure.dependencies.current_user import require_permiso

router = APIRouter()


@router.get("/movimientos", response_model=List[MovimientoItem])
async def listar_movimientos(producto: Optional[int] = None):
    """Kardex de inventario (historial de movimientos). Acotado por RLS al taller."""
    return await InventarioServicio().listar_movimientos(producto)


@router.get("/productos", response_model=List[ProductoStock])
async def listar_productos():
    """Productos con su stock (para las pantallas de entrada y toma física)."""
    return await InventarioServicio().listar_productos()


# El catálogo de permisos no tiene un recurso "inventario" propio; ambas
# operaciones mutan productos.stock_pro, así que reusan "actualizar:productos"
# (F0-11) en vez de agregar permisos nuevos que requerirían una migración.
@router.post("/entrada", status_code=HTTP_201_CREATED)
async def registrar_entrada(
    contract: EntradaContract,
    current: Dict = Depends(require_permiso("actualizar:productos")),
):
    """Registra una entrada de stock (reabastecimiento). Solo Admin/Recepcionista."""
    return await InventarioServicio().entrada(current, contract)


@router.post("/toma-fisica")
async def toma_fisica(
    contract: TomaFisicaContract,
    current: Dict = Depends(require_permiso("actualizar:productos")),
):
    """Aplica una toma física: ajusta el stock a las cantidades contadas y registra
    los movimientos AJUSTE. Solo Admin/Recepcionista."""
    return await InventarioServicio().toma_fisica(current, contract)
