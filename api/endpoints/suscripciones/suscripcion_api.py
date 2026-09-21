from typing import Dict, List

from fastapi import APIRouter, Depends

from domain.contracts.suscripciones.suscripcion_contract import (
    CheckoutContract,
    CheckoutResponseContract,
    PlanContract,
)
from domain.services.suscripciones.suscripcion_servicio import SuscripcionServicio
from infrastructure.dependencies.current_user import require_admin

router = APIRouter()


@router.get("/planes", response_model=List[PlanContract])
async def listar_planes():
    """Catálogo de planes (para la pantalla de precios/suscripción)."""
    return await SuscripcionServicio().listar_planes()


@router.post("/checkout", response_model=CheckoutResponseContract)
async def crear_checkout(contract: CheckoutContract, current: Dict = Depends(require_admin)):
    """Genera el link de pago de Wompi para el plan elegido (solo Admin del taller)."""
    return await SuscripcionServicio().crear_checkout(current.get("COD_TALLER"), contract.plan)


@router.get("/pagos")
async def listar_pagos(current: Dict = Depends(require_admin)):
    """Historial de pagos del taller."""
    return await SuscripcionServicio().listar_pagos(current.get("COD_TALLER"))
