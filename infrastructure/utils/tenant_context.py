"""Contexto del taller (tenant) para la petición actual.

Se setea por request (ver infrastructure/dependencies/tenant_request.py) y lo lee
la capa de datos (Database) para hacer SET app.tenant_id en cada consulta. El RLS de Postgres hace el
aislamiento; aquí solo transportamos el id del taller a través del request.
"""
from contextvars import ContextVar
from typing import Optional

_tenant: ContextVar[Optional[int]] = ContextVar("cod_taller", default=None)


def set_tenant(cod_taller: Optional[int]) -> None:
    _tenant.set(cod_taller)


def get_tenant() -> Optional[int]:
    return _tenant.get()
