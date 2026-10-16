from fastapi import APIRouter

from api.endpoints.superadmin.acciones_taller_api import router as acciones_router
from api.endpoints.superadmin.pagos_superadmin_api import router as pagos_router
from api.endpoints.superadmin.resumen_api import router as resumen_router
from api.endpoints.superadmin.talleres_superadmin_api import router as talleres_router

# Un solo router lógico (Resumen + Talleres + Acciones + Pagos) para que
# api/__init__.py le aplique require_super_admin UNA sola vez a nivel de router
# (F0-14), en vez de uno por sub-archivo.
router = APIRouter()
router.include_router(resumen_router)
router.include_router(talleres_router)
router.include_router(acciones_router)
router.include_router(pagos_router)
