from typing import Dict, Optional

from fastapi import APIRouter, Depends

from domain.contracts.shared.respuesta_contract import CambioEstadoTableroResponseContract
from domain.models.tablero.tablero_model import (
    AgregarNotaContract,
    CambiarEstadoContract,
    NotaTableroResponse,
    TableroResponse,
)
from domain.services.tablero.tablero_servicio import TableroServicio
from infrastructure.dependencies.current_user import get_current_usuario, require_permiso

router = APIRouter()


@router.get("", response_model=TableroResponse)
async def obtener_tablero(
    mecanico: Optional[str] = None,
    current: Optional[Dict] = Depends(get_current_usuario),
):
    """Tablero de órdenes. El alcance lo decide el ROL del usuario:
    el mecánico solo ve las suyas; admin/recepcionista ven todo o el mecánico seleccionado."""
    return await TableroServicio().obtener(current, mecanico)


@router.put("/{consecutivo_ot}/estado", response_model=CambioEstadoTableroResponseContract)
async def cambiar_estado(
    consecutivo_ot: int,
    contract: CambiarEstadoContract,
    current: Dict = Depends(require_permiso("crear_editar:ordenes-trabajo")),
):
    """Cambia el estado de una OT (arrastrar en el tablero). Reglas por rol:
    mecánico solo sus OT y a Pendiente/En Proceso/Completada; admin/recep cualquiera."""
    return await TableroServicio().cambiar_estado(
        current, consecutivo_ot, contract.cod_estado, contract.confirmar_credito
    )


@router.patch("/{consecutivo_ot}/nota", response_model=NotaTableroResponse)
async def agregar_nota(
    consecutivo_ot: int,
    contract: AgregarNotaContract,
    current: Dict = Depends(require_permiso("crear_editar:ordenes-trabajo")),
):
    """F1-08: agrega una nota a la observación interna (ej. "Necesito
    repuesto") sin cambiar el estado. Mismo alcance que /estado: mecánico
    solo en sus propias OT."""
    return await TableroServicio().agregar_nota(current, consecutivo_ot, contract.nota)
