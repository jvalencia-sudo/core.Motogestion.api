"""Filtro before_send de Sentry: redacta datos sensibles antes de enviar un evento.

`send_default_pii=False` en sentry_sdk.init ya evita mandar cookies/headers/IP por
defecto, pero Sentry sí captura variables locales de cada frame del stack trace — ahí
puede terminar una contraseña o un documento de cliente como variable local de la
función que falló. Este filtro recorre el evento (request, extra y los locals de
cada frame) y redacta cualquier clave de la lista negra, sin importar dónde aparezca.
"""
from typing import Any

_CLAVES_SENSIBLES = {
    "password",
    "contrasena_usu",
    "documento_cli",
    "documento_cli_mot",
    "authorization",
    "token",
    "cookie",
    "access_token",
    "client_secret",
}


def _redactar(valor: Any) -> Any:
    if isinstance(valor, dict):
        return {
            k: "[REDACTADO]" if k.lower() in _CLAVES_SENSIBLES else _redactar(v)
            for k, v in valor.items()
        }
    if isinstance(valor, list):
        return [_redactar(v) for v in valor]
    return valor


def scrub_before_send(event: dict, hint: dict) -> dict:
    if "request" in event:
        event["request"] = _redactar(event["request"])
    if "extra" in event:
        event["extra"] = _redactar(event["extra"])

    for exc in event.get("exception", {}).get("values", []):
        for frame in exc.get("stacktrace", {}).get("frames", []):
            if "vars" in frame:
                frame["vars"] = _redactar(frame["vars"])

    return event
