from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, status

from domain.contracts.superadmin.taller_superadmin_contract import (
    CrearNotaContract,
    NotaTallerContract,
    TallerDetalleContract,
    TallerListadoContract,
)
from domain.contracts.talleres.taller_contract import TallerRegistroContract, TallerRegistroResponse
from domain.services.superadmin.talleres_superadmin_servicio import TalleresSuperAdminServicio
from infrastructure.dependencies.current_user import get_current_usuario

router = APIRouter()


@router.get("/talleres", response_model=List[TallerListadoContract])
async def listar_talleres(estado: Optional[str] = None):
    """Lista de talleres con estado, precio pactado, último pago y uso de los
    últimos 7/30 días. Filtrable por estado."""
    return await TalleresSuperAdminServicio().listar(estado)


@router.get("/talleres/{cod_taller}", response_model=TallerDetalleContract)
async def obtener_detalle_taller(cod_taller: int):
    """Detalle de un taller: datos, historial de pagos, usuarios, métricas y notas."""
    return await TalleresSuperAdminServicio().detalle(cod_taller)


@router.post("/talleres", response_model=TallerRegistroResponse, status_code=status.HTTP_201_CREATED)
async def crear_taller_manual(contract: TallerRegistroContract):
    """Crea un taller a mano desde el panel; el dueño recibe la invitación por
    correo (mismo flujo que el registro público)."""
    return await TalleresSuperAdminServicio().crear_manual(contract)


@router.post("/talleres/{cod_taller}/notas", response_model=NotaTallerContract, status_code=status.HTTP_201_CREATED)
async def crear_nota(cod_taller: int, contract: CrearNotaContract, current: Dict = Depends(get_current_usuario)):
    """Nota interna sobre un taller (no es dato del tenant, no queda en auditoría
    de acciones -- es solo un apunte, no un cambio de estado)."""
    autor = str(current.get("DOCUMENTO_USU")) if current else "desconocido"
    return await TalleresSuperAdminServicio().crear_nota(cod_taller, contract, autor)
