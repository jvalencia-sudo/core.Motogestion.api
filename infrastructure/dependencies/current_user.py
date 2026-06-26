"""Dependencias para identificar al usuario actual desde el token y aplicar gateos.

- get_current_usuario: devuelve el registro de BD del usuario (o None si no se puede
  resolver). Reusa el contexto de tenant que ya fijó resolve_tenant (RLS).
- require_super_admin: exige que el usuario sea Admin del taller plataforma.

El sistema de permisos por endpoint del backend estaba dormido; estas dependencias son
el guardia mínimo para los endpoints sensibles (gestión de talleres, auto-edición de rol).
"""
from typing import Dict, Optional

from fastapi import Request
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN

from infrastructure.exceptions.domain_exception import DomainException
from infrastructure.providers.auth.auth0_provider import Auth0Provider
from repository.auth.user_repository import UserRepository

# Taller plataforma: sus administradores son los super-admin del sistema.
PLATFORM_TALLER = 1
ADMIN_ROL = 1


async def get_current_usuario(request: Request) -> Optional[Dict]:
    """Resuelve el usuario de BD a partir del Bearer token. None si no se puede.

    No lanza: es para gateos que solo aplican cuando se conoce al usuario (p.ej.
    impedir que alguien cambie su propio rol). resolve_tenant ya fijó el tenant,
    así que get_user_by_sub respeta el RLS del taller del usuario.
    """
    authorization = request.headers.get("authorization", "")
    if not authorization.lower().startswith("bearer "):
        return None
    token = authorization[7:].strip()
    try:
        auth_user = await Auth0Provider().verify(token)
        return await UserRepository().get_user_by_sub(auth_user.user_id)
    except Exception:
        return None


async def require_super_admin(request: Request) -> Dict:
    """Exige Admin del taller plataforma. Lanza 401/403 si no cumple (fail-closed)."""
    user = await get_current_usuario(request)
    if user is None:
        raise DomainException("No autenticado", HTTP_401_UNAUTHORIZED)
    if user.get("COD_TALLER") != PLATFORM_TALLER or user.get("COD_ROL_PRF_USU") != ADMIN_ROL:
        raise DomainException("Requiere permisos de super-administrador", HTTP_403_FORBIDDEN)
    return user


def assert_no_self_role_change(
    target_documento: str,
    nuevo_prf: Optional[int],
    nuevo_rol: Optional[int],
    current: Optional[Dict],
) -> None:
    """Impide que un usuario cambie su PROPIO rol/perfil (evita auto-degradarse).

    Solo aplica cuando se identifica al llamante y edita su propio documento. Permite
    guardar otros campos (nombre, correo) si no toca rol/perfil. Si no se pudo
    identificar al llamante, el guard no aplica (la seguridad real es el RLS).
    """
    if current is None:
        return
    if str(current.get("DOCUMENTO_USU")) != str(target_documento):
        return
    cambia_prf = nuevo_prf is not None and nuevo_prf != current.get("COD_PRF_USU")
    cambia_rol = nuevo_rol is not None and nuevo_rol != current.get("COD_ROL_PRF_USU")
    if cambia_prf or cambia_rol:
        raise DomainException("No puedes cambiar tu propio rol o perfil", HTTP_403_FORBIDDEN)
