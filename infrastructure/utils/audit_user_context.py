"""Contexto del usuario autenticado para la petición actual (F1-05).

Se setea por request (ver infrastructure/dependencies/tenant_request.py) junto
con el tenant, y lo lee la capa de datos (Database) para hacer
set_config('app.usuario', ...) en cada consulta. fn_audit() lo usa para dejar
en audit_log QUIÉN hizo cada cambio, en vez de siempre `session_user` (el rol
de la app, mt_app).
"""
from contextvars import ContextVar
from typing import Optional

_usuario: ContextVar[Optional[str]] = ContextVar("documento_usu_actual", default=None)


def set_audit_user(documento_usu: Optional[str]) -> None:
    _usuario.set(documento_usu)


def get_audit_user() -> Optional[str]:
    return _usuario.get()
