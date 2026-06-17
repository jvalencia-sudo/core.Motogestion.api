from fastapi import APIRouter

from api.endpoints.auth.user_api import router as users_router
from api.endpoints.auth.rol import router as rol_router
from api.endpoints.auth.perfil import router as perfil_router
from api.endpoints.auth.permiso import router as permiso_router
from api.endpoints.auth.perfil_permiso import router as perfil_permiso_router
from api.endpoints.auth.vista import router as vista_router
from api.endpoints.admin.user_admin_api import router as admin_users_router
from api.endpoints.productos.producto_api import router as productos_router
from api.endpoints.marcas.marca_api import router as marcas_router
from api.endpoints.clientes.cliente_api import router as clientes_router
from api.endpoints.motos.moto_api import router as motos_router
from api.endpoints.ordenes_trabajo.orden_trabajo_api import router as ordenes_trabajo_router
from api.endpoints.ordenes_trabajo.reclamo_api import router as reclamos_router

api_router = APIRouter()

api_router.include_router(rol_router, prefix="/rol", tags=["Auth"])
api_router.include_router(
    users_router, prefix="/auth", tags=["Auth"]
)
api_router.include_router(perfil_router, prefix="/perfil", tags=["Auth"])
api_router.include_router(perfil_permiso_router, prefix="/perfil-permiso", tags=["Auth"])

api_router.include_router(vista_router, prefix="/vista", tags=["Auth"])
api_router.include_router(permiso_router, prefix="/permiso", tags=["Auth"])

# Admin endpoints
api_router.include_router(admin_users_router, prefix="/admin/users", tags=["Admin"])

# Productos endpoints
api_router.include_router(productos_router, prefix="/productos", tags=["Productos"])

# Marcas, Clientes y Motos endpoints
api_router.include_router(marcas_router, prefix="/marcas", tags=["Motos"])
api_router.include_router(clientes_router, prefix="/clientes", tags=["Clientes"])
api_router.include_router(motos_router, prefix="/motos", tags=["Motos"])

# Ordenes de Trabajo endpoints
api_router.include_router(ordenes_trabajo_router, tags=["Ordenes de Trabajo"])

# Reclamos endpoints
api_router.include_router(reclamos_router, tags=["Reclamos"])
