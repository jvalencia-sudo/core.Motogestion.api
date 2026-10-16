from fastapi import APIRouter

from domain.contracts.superadmin.resumen_contract import ResumenPlataformaContract
from domain.services.superadmin.resumen_servicio import ResumenServicio

router = APIRouter()


@router.get("/resumen", response_model=ResumenPlataformaContract)
async def obtener_resumen():
    """Tablero de negocio del super-admin: MRR, talleres por estado, cupos
    fundador, vencimientos próximos y conversión prueba->pago."""
    return await ResumenServicio().obtener()
