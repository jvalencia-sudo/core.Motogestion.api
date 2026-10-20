"""Dependency global: resuelve el taller (tenant) de la petición.

Lee el Bearer token, lo valida con Auth0, busca el taller del usuario y lo deja en
el contexto (tenant_context). La capa de datos lo usa para fijar app.tenant_id y el RLS de
Postgres aísla los datos. Si no hay token o el usuario no tiene taller, queda sin
taller: el RLS no devolverá nada (aislamiento seguro por defecto), sin lanzar error.
"""
from fastapi import Request

from infrastructure.providers.auth.auth0_provider import Auth0Provider
from infrastructure.utils.audit_user_context import set_audit_user
from infrastructure.utils.permission_context import set_cached_permisos
from infrastructure.utils.tenant_context import set_tenant
from infrastructure.utils.user_context import set_current_user_id
from repository.auth.identidad_repositorio import IdentidadRepositorio


async def resolve_tenant(request: Request) -> None:
    set_tenant(None)
    set_current_user_id(None)
    set_cached_permisos(None)
    set_audit_user(None)
    authorization = request.headers.get("authorization", "")
    if not authorization.lower().startswith("bearer "):
        return

    token = authorization[7:].strip()
    try:
        auth_user = await Auth0Provider().verify(token)
        set_current_user_id(auth_user.user_id)
        acceso = await IdentidadRepositorio().get_taller_y_documento_by_sub(auth_user.user_id)
        if acceso:
            set_tenant(acceso.get("COD_TALLER"))
            set_audit_user(acceso.get("DOCUMENTO_USU"))
        else:
            set_tenant(None)
    except Exception:
        # Token inválido o usuario sin taller: se queda sin tenant (RLS = sin datos).
        set_tenant(None)
