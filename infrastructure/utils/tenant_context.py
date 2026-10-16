"""Contexto del taller (tenant) para la petición actual.

Se setea por request (ver infrastructure/dependencies/tenant_request.py) y lo lee
la capa de datos (Database) para hacer SET app.tenant_id en cada consulta. El RLS de Postgres hace el
aislamiento; aquí solo transportamos el id del taller a través del request.
"""
from contextvars import ContextVar, Token
from typing import Optional

_tenant: ContextVar[Optional[int]] = ContextVar("cod_taller", default=None)


def set_tenant(cod_taller: Optional[int]) -> Token:
    """Devuelve el Token de este `set`, para quien necesite restaurar el valor
    anterior con `reset_tenant` (ver su docstring) en vez de dejarlo pisado
    para el resto del request."""
    return _tenant.set(cod_taller)


def reset_tenant(token: Token) -> None:
    """Restaura `app.tenant_id` al valor que tenía antes de un `set_tenant`
    puntual (ej. recorrer varios talleres dentro de un mismo request de
    super-admin). Sin esto, una consulta posterior a una tabla con RLS en ese
    mismo request vería los datos del último tenant recorrido, no el del
    caller -- un request nuevo lo vuelve a fijar desde cero vía
    `resolve_tenant`, pero dentro del MISMO request no hay nada que lo arregle
    solo."""
    _tenant.reset(token)


def get_tenant() -> Optional[int]:
    return _tenant.get()
