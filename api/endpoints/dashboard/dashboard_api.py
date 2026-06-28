from fastapi import APIRouter

from domain.models.dashboard.dashboard_model import ResumenDashboard
from domain.services.dashboard.dashboard_servicio import DashboardServicio

router = APIRouter()


@router.get("/resumen", response_model=ResumenDashboard)
async def resumen():
    """Resumen del taller para la home (KPIs + órdenes por estado). Acotado por RLS."""
    return await DashboardServicio().resumen()
