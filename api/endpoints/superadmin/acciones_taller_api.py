from typing import Dict

from fastapi import APIRouter, Depends

from domain.contracts.superadmin.accion_taller_contract import (
    AjustarPrecioContract,
    ExtenderPruebaContract,
    PagoManualContract,
    SuspenderReactivarContract,
)
from domain.services.superadmin.acciones_taller_servicio import AccionesTallerServicio
from infrastructure.dependencies.current_user import get_current_usuario

router = APIRouter()


def _usuario(current: Dict) -> str:
    """Quién hizo la acción, para la auditoría -- no autoriza (require_super_admin
    ya se aplica a nivel de router, ver api/__init__.py)."""
    return str(current.get("DOCUMENTO_USU")) if current else "desconocido"


@router.post("/talleres/{cod_taller}/extender-prueba")
async def extender_prueba(
    cod_taller: int, contract: ExtenderPruebaContract, current: Dict = Depends(get_current_usuario)
):
    return await AccionesTallerServicio().extender_prueba(cod_taller, contract, _usuario(current))


@router.post("/talleres/{cod_taller}/pago-manual")
async def pago_manual(
    cod_taller: int, contract: PagoManualContract, current: Dict = Depends(get_current_usuario)
):
    return await AccionesTallerServicio().pago_manual(cod_taller, contract, _usuario(current))


@router.post("/talleres/{cod_taller}/suspender")
async def suspender(
    cod_taller: int, contract: SuspenderReactivarContract, current: Dict = Depends(get_current_usuario)
):
    return await AccionesTallerServicio().suspender(cod_taller, contract, _usuario(current))


@router.post("/talleres/{cod_taller}/reactivar")
async def reactivar(
    cod_taller: int, contract: SuspenderReactivarContract, current: Dict = Depends(get_current_usuario)
):
    return await AccionesTallerServicio().reactivar(cod_taller, contract, _usuario(current))


@router.put("/talleres/{cod_taller}/precio")
async def ajustar_precio(
    cod_taller: int, contract: AjustarPrecioContract, current: Dict = Depends(get_current_usuario)
):
    return await AccionesTallerServicio().ajustar_precio(cod_taller, contract, _usuario(current))
