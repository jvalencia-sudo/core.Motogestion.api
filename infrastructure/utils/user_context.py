"""Contexto del usuario (sub de Auth0) para la petición actual.

Mismo patrón que tenant_context.py: se setea por request (ver
infrastructure/dependencies/tenant_request.py, que ya resuelve el sub del token al
verificarlo) y lo lee el middleware de logging para incluir "usuario" en cada línea
de log sin tener que volver a verificar el token.
"""
from contextvars import ContextVar
from typing import Optional

_user_id: ContextVar[Optional[str]] = ContextVar("user_id", default=None)


def set_current_user_id(user_id: Optional[str]) -> None:
    _user_id.set(user_id)


def get_current_user_id() -> Optional[str]:
    return _user_id.get()
