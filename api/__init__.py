from fastapi import APIRouter, Depends

from infrastructure.dependencies.current_user import require_active_subscription
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
from api.endpoints.talleres.taller_api import router as talleres_router
from api.endpoints.dashboard.dashboard_api import router as dashboard_router
from api.endpoints.tablero.tablero_api import router as tablero_router
from api.endpoints.inventario.inventario_api import router as inventario_router
from api.endpoints.impuestos.impuesto_api import router as impuestos_router
from api.endpoints.suscripciones.suscripcion_api import router as suscripciones_router
from api.endpoints.public.wompi_webhook_api import router as wompi_webhook_router

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

# Los routers OPERATIVOS exigen suscripción vigente (trial no vencido / activo).
_susc = [Depends(require_active_subscription)]

# Productos endpoints
api_router.include_router(productos_router, prefix="/productos", tags=["Productos"], dependencies=_susc)

# Marcas, Clientes y Motos endpoints
api_router.include_router(marcas_router, prefix="/marcas", tags=["Motos"], dependencies=_susc)
api_router.include_router(clientes_router, prefix="/clientes", tags=["Clientes"], dependencies=_susc)
api_router.include_router(motos_router, prefix="/motos", tags=["Motos"], dependencies=_susc)

# Ordenes de Trabajo endpoints
api_router.include_router(ordenes_trabajo_router, tags=["Ordenes de Trabajo"], dependencies=_susc)

# Reclamos endpoints
api_router.include_router(reclamos_router, tags=["Reclamos"], dependencies=_susc)

# Talleres (registro / onboarding)
api_router.include_router(talleres_router, prefix="/talleres", tags=["Talleres"])

# Dashboard (resumen para la home)
api_router.include_router(dashboard_router, prefix="/dashboard", tags=["Dashboard"])

# Tablero (órdenes de trabajo, alcance por rol)
api_router.include_router(tablero_router, prefix="/tablero", tags=["Tablero"], dependencies=_susc)

# Inventario (movimientos de stock, entradas, toma física)
api_router.include_router(inventario_router, prefix="/inventario", tags=["Inventario"], dependencies=_susc)

# Impuestos (catálogo del taller para asignar a productos)
api_router.include_router(impuestos_router, prefix="/impuestos", tags=["Impuestos"], dependencies=_susc)

# Suscripciones / planes / pagos (NO gateado: un taller vencido debe poder pagar)
api_router.include_router(suscripciones_router, prefix="/suscripciones", tags=["Suscripciones"])

# Webhook público de Wompi (sin auth; validado por firma del evento)
api_router.include_router(wompi_webhook_router, prefix="/public", tags=["Public"])
