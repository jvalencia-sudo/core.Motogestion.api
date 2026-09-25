"""Plantilla de ruta (p.ej. `/api/clientes/{documento_cli}`), no la ruta resuelta
con el valor real. Starlette deja la Route ya emparejada en `scope["route"]`
después de que el router la resuelve -- se usa en vez de `scope["path"]`/
`request.url.path` en todo lo que se loguea o se manda a Sentry, para no dejar
documentos/placas/ids en texto plano.
"""
from starlette.types import Scope


def ruta_plantilla(scope: Scope) -> str:
    route = scope.get("route")
    path = getattr(route, "path", None)
    return path if path is not None else scope.get("path", "")
