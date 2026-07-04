from typing import Dict, Optional

from fastapi import APIRouter, Depends

from domain.models.tablero.tablero_model import CambiarEstadoContract, TableroResponse
from domain.services.tablero.tablero_servicio import TableroServicio
from infrastructure.dependencies.current_user import get_current_usuario

router = APIRouter()


@router.get("", response_model=TableroResponse)
async def obtener_tablero(
    mecanico: Optional[str] = None,
    current: Optional[Dict] = Depends(get_current_usuario),
):
    """Tablero de órdenes. El alcance lo decide el ROL del usuario:
    el mecánico solo ve las suyas; admin/recepcionista ven todo o el mecánico seleccionado."""
    return await TableroServicio().obtener(current, mecanico)


@router.put("/{consecutivo_ot}/estado")
async def cambiar_estado(
    consecutivo_ot: int,
    contract: CambiarEstadoContract,
    current: Optional[Dict] = Depends(get_current_usuario),
):
    """Cambia el estado de una OT (arrastrar en el tablero). Reglas por rol:
    mecánico solo sus OT y a Pendiente/En Proceso/Completada; admin/recep cualquiera."""
    return await TableroServicio().cambiar_estado(current, consecutivo_ot, contract.cod_estado)
