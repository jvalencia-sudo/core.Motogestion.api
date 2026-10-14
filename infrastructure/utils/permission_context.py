"""Caché de permisos del usuario actual para la petición (ContextVar).

Mismo patrón que tenant_context.py / user_context.py. require_permiso puede pedirse
más de una vez en la misma petición (varias dependencias apiladas, o un mismo
endpoint con permisos compuestos): esto evita repetir la consulta a
perfiles_permisos en cada una. Se resetea al inicio de cada petición en
resolve_tenant, igual que tenant/usuario.
"""
from contextvars import ContextVar
from typing import Optional, Set

_permisos: ContextVar[Optional[Set[str]]] = ContextVar("permisos_usuario", default=None)


def set_cached_permisos(permisos: Optional[Set[str]]) -> None:
    _permisos.set(permisos)


def get_cached_permisos() -> Optional[Set[str]]:
    return _permisos.get()
