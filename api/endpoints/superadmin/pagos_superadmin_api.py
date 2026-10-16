from typing import List, Optional

from fastapi import APIRouter

from domain.contracts.superadmin.pago_superadmin_contract import AlertasPagoContract, PagoPlataformaContract
from domain.services.superadmin.pagos_superadmin_servicio import PagosSuperAdminServicio

router = APIRouter()


@router.get("/pagos/alertas", response_model=AlertasPagoContract)
async def obtener_alertas():
    """Pago aprobado sin suscripción activa, y pendientes hace más de un día."""
    return await PagosSuperAdminServicio().alertas()


@router.get("/pagos", response_model=List[PagoPlataformaContract])
async def listar_pagos(estado: Optional[str] = None, medio: Optional[str] = None):
    """Pagos de todos los talleres, filtrable por estado y medio (Wompi/manual)."""
    return await PagosSuperAdminServicio().listar(estado, medio)
