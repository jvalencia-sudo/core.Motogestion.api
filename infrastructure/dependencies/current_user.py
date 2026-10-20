"""Dependencias para identificar al usuario actual desde el token y aplicar gateos.

- get_current_usuario: devuelve el registro de BD del usuario (o None si no se puede
  resolver). Reusa el contexto de tenant que ya fijó resolve_tenant (RLS).
- require_super_admin: exige la marca es_super_admin (F0-14), independiente de a qué
  taller pertenezca el usuario o qué rol tenga ahí.
- require_permiso: exige un permiso puntual (tabla perfiles_permisos) del perfil del
  usuario, o que sea Administrador (pasa siempre). Es el guardia real por acción
  (F0-11): antes del backend no validaba nada de esto, solo lo ocultaba el front.

El sistema de permisos por endpoint del backend estaba dormido; estas dependencias son
el guardia mínimo para los endpoints sensibles (gestión de talleres, auto-edición de rol).
"""
from typing import Callable, Dict, Optional, Set

from fastapi import Request
from starlette.status import (
    HTTP_401_UNAUTHORIZED,
    HTTP_402_PAYMENT_REQUIRED,
    HTTP_403_FORBIDDEN,
)

from infrastructure.exceptions.domain_exception import DomainException
from infrastructure.providers.auth.auth0_provider import Auth0Provider
from infrastructure.utils.fecha_bogota import hoy_bogota
from infrastructure.utils.permission_context import get_cached_permisos, set_cached_permisos
from repository.auth.perfil_permiso_repositorio import PerfilPermisoRepositorio
from repository.auth.user_repository import UserRepository
from repository.talleres.taller_repositorio import TallerRepositorio
from repository.planes.plan_repositorio import PlanRepositorio


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
    """Exige es_super_admin=true (F0-14). Lanza 401/403 si no cumple (fail-closed).

    Antes de F0-14 esto exigía "Admin del taller plataforma (cod_taller=1)" -- un
    taller hardcodeado que también se usaba para demos: si alguien recibía rol Admin
    ahí por error, quedaba con acceso a toda la plataforma sin que nadie lo decidiera.
    Ahora es una marca explícita e independiente de cualquier taller/rol, otorgada
    solo por SQL directo (no hay UI para darla, a propósito)."""
    user = await get_current_usuario(request)
    if user is None:
        raise DomainException("No autenticado", HTTP_401_UNAUTHORIZED)
    if not user.get("ES_SUPER_ADMIN"):
        raise DomainException("Requiere permisos de super-administrador", HTTP_403_FORBIDDEN)
    return user


async def require_admin(request: Request) -> Dict:
    """Exige que el usuario sea Administrador de SU propio taller. Para acciones de
    gestión dentro del taller (p.ej. invitar miembros). Fail-closed: 401/403."""
    user = await get_current_usuario(request)
    if user is None:
        raise DomainException("No autenticado", HTTP_401_UNAUTHORIZED)
    if not user.get("ES_ADMIN_USU"):
        raise DomainException("Requiere permisos de administrador", HTTP_403_FORBIDDEN)
    return user


async def require_active_subscription(request: Request) -> Dict:
    """Exige que la suscripción del taller esté vigente. Fail-closed:
    - suspendido -> 403
    - prueba vencida (fecha_fin_susc_tal < hoy) -> 402 (Payment Required)
    - activo / prueba vigente -> pasa.
    Se aplica a los routers operativos (productos, órdenes, inventario, etc.)."""
    user = await get_current_usuario(request)
    if user is None:
        raise DomainException("No autenticado", HTTP_401_UNAUTHORIZED)
    susc = await TallerRepositorio().get_suscripcion(user.get("COD_TALLER"))
    if not susc:
        raise DomainException("Taller no encontrado", HTTP_403_FORBIDDEN)
    estado = susc.get("ESTADO_TAL")
    fecha_fin = susc.get("FECHA_FIN_SUSC_TAL")
    if estado == "suspendido":
        raise DomainException("La suscripción del taller está suspendida.", HTTP_403_FORBIDDEN)
    if estado == "prueba" and fecha_fin is not None and fecha_fin < hoy_bogota():
        raise DomainException(
            "Tu período de prueba terminó. Activa un plan para continuar.",
            HTTP_402_PAYMENT_REQUIRED,
        )
    return user


def require_feature(feature: str):
    """Depends factory: exige que el plan del taller incluya `feature`. Durante la
    prueba vigente el taller tiene todas las features; si es 'activo' se valida contra
    `planes.features` de su `plan_tal`."""
    async def _dep(request: Request) -> Dict:
        user = await require_active_subscription(request)  # además valida vigencia
        susc = await TallerRepositorio().get_suscripcion(user.get("COD_TALLER"))
        if susc.get("ESTADO_TAL") == "prueba":
            return user  # trial: acceso a todo
        features = await PlanRepositorio().features_de(susc.get("PLAN_TAL"))
        if not features.get(feature):
            raise DomainException(
                f"Tu plan no incluye esta función ({feature}). Actualiza tu plan.",
                HTTP_403_FORBIDDEN,
            )
        return user

    return _dep


async def _permisos_del_usuario(user: Dict) -> Set[str]:
    """Permisos activos del perfil del usuario, cacheados por petición.

    Usa vw_perfiles_permisos_detalle (vía PerfilPermisoRepositorio), que no expone
    cod_est_pp crudo sino el nombre del estado ya resuelto ("Activo"/"Inactivo").
    """
    cache = get_cached_permisos()
    if cache is not None:
        return cache
    filas = await PerfilPermisoRepositorio().obtener_permisos_por_perfil(
        user.get("COD_PRF_USU")
    )
    permisos = {f.get("NOMBRE_PRM") for f in filas if f.get("ESTADO_PERMISO") == "Activo"}
    set_cached_permisos(permisos)
    return permisos


async def usuario_tiene_permiso(user: Optional[Dict], nombre_prm: str) -> bool:
    """Chequeo de permiso fuera del flujo Depends -- para gateos que dependen del
    contenido del body, no de toda la ruta (p.ej. F1-06: solo bloquea si el body
    trae cobrar_deto=False en algún ítem, no cualquier POST/PATCH de la orden)."""
    if user is None:
        return False
    if user.get("ES_ADMIN_USU"):
        return True
    permisos = await _permisos_del_usuario(user)
    return nombre_prm in permisos


def require_permiso(nombre_prm: str) -> Callable:
    """Depends factory: exige el permiso `nombre_prm` (formato "accion:recurso",
    ej. "eliminar_o_anular:productos") asignado y activo en el perfil del usuario.
    El Administrador siempre pasa, sin consultar perfiles_permisos. Fail-closed:
    401 sin token válido, 403 sin el permiso."""

    async def _dep(request: Request) -> Dict:
        user = await get_current_usuario(request)
        if user is None:
            raise DomainException("No autenticado", HTTP_401_UNAUTHORIZED)
        if not await usuario_tiene_permiso(user, nombre_prm):
            raise DomainException(f"No tienes el permiso '{nombre_prm}'", HTTP_403_FORBIDDEN)
        return user

    return _dep


def assert_no_self_role_change(
    target_documento: str,
    nuevo_prf: Optional[int],
    current: Optional[Dict],
) -> None:
    """Impide que un usuario cambie su PROPIO rol (evita auto-degradarse).

    El estado admin/no-admin se deriva siempre del perfil (F1-12: es_admin es
    una columna de `perfiles`, 1:1 por perfil), así que basta con comparar el
    perfil -- no puede cambiar de admin sin cambiar el perfil. Solo aplica cuando se identifica
    al llamante y edita su propio documento. Permite guardar otros campos (nombre,
    correo) si no toca el perfil. Si no se pudo identificar al llamante, el guard
    no aplica (la seguridad real es el RLS).
    """
    if current is None:
        return
    if str(current.get("DOCUMENTO_USU")) != str(target_documento):
        return
    if nuevo_prf is not None and nuevo_prf != current.get("COD_PRF_USU"):
        raise DomainException("No puedes cambiar tu propio rol", HTTP_403_FORBIDDEN)
