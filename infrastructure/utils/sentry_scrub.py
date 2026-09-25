"""Filtro before_send de Sentry: redacta datos sensibles antes de enviar un evento.

`send_default_pii=False` e `include_local_variables=False` en sentry_sdk.init ya
evitan mandar cookies/headers/IP y variables locales por defecto, pero quedan tres
caminos que ese par de flags no cubre, y que este filtro sí:

1. La URL real de la petición (`event["request"]["url"]`, y la de cada breadcrumb
   HTTP/navegación) trae el documento/placa en el path -- p.ej.
   `/api/clientes/1122334455`. El scrub por clave no alcanza porque es texto, no
   un diccionario con una clave "documento_cli". Se reemplaza cada segmento que
   *parece* un valor real (dígitos largos, o 6 alfanuméricos tipo placa) por
   "{id}", y se descarta el query string entero.
2. Los errores de Postgres agregan una línea "DETAIL: Key (documento_cli)=(...)
   already exists" con la fila real -- viene en el propio `str(exc)`, así que
   aparece en `event["exception"][...]["value"]` sin importar qué tan poco
   loguee el handler. Se corta esa línea de cualquier texto del evento.
3. El resto (password, documento, tokens, etc.) sigue redactándose por clave en
   request/extra/vars, con la lista ampliada.
"""
import re
from typing import Any
from urllib.parse import urlsplit, urlunsplit

_CLAVES_SENSIBLES = {
    "password",
    "contrasena_usu",
    "documento_cli",
    "documento_cli_mot",
    "documento_usu",
    "documento_usu_mc_ot",
    "telefono_cli",
    "correo_cli",
    "email",
    "authorization",
    "token",
    "cookie",
    "access_token",
    "client_secret",
}

# Segmento de ruta que es un valor real, no parte fija de la URL: documentos/ids
# (4+ dígitos) o placas (6 alfanuméricos con al menos un dígito). El dígito
# obligatorio es clave: sin él, palabras de 6 letras que sí son parte fija de la
# URL (p.ej. "config" en /talleres/config, "planes" en /suscripciones/planes)
# quedarían redactadas por error -- se comprobó con un test que fallaba así.
_SEGMENTO_VALOR = re.compile(r"^\d{4,}$|^(?=[A-Za-z0-9]*\d)[A-Za-z0-9]{6}$")

# Postgres agrega esta línea a los mensajes de restricción con la fila real que
# las violó (p.ej. "DETAIL:  Key (documento_cli)=(1122334455) already exists.").
_DETAIL_LINEA = re.compile(r"(?im)^\s*DETAIL:.*$")


def _limpiar_url(url: str) -> str:
    try:
        partes = urlsplit(url)
    except ValueError:
        return url
    segmentos = [
        "{id}" if _SEGMENTO_VALOR.match(s) else s for s in partes.path.split("/")
    ]
    # El query string también puede llevar valores (?documento=...): se descarta
    # entero en vez de intentar filtrar parámetro por parámetro.
    return urlunsplit((partes.scheme, partes.netloc, "/".join(segmentos), "", partes.fragment))


def _limpiar_texto(valor: str) -> str:
    return _DETAIL_LINEA.sub("[DETAIL REDACTADO]", valor)


def _redactar(valor: Any) -> Any:
    if isinstance(valor, dict):
        return {
            k: "[REDACTADO]" if k.lower() in _CLAVES_SENSIBLES else _redactar(v)
            for k, v in valor.items()
        }
    if isinstance(valor, list):
        return [_redactar(v) for v in valor]
    if isinstance(valor, str):
        return _limpiar_texto(valor)
    return valor


def _limpiar_breadcrumbs(event: dict) -> None:
    for crumb in event.get("breadcrumbs", {}).get("values", []):
        data = crumb.get("data")
        if isinstance(data, dict) and isinstance(data.get("url"), str):
            data["url"] = _limpiar_url(data["url"])
        if isinstance(crumb.get("message"), str):
            crumb["message"] = _limpiar_texto(crumb["message"])


def scrub_before_send(event: dict, hint: dict) -> dict:
    if "request" in event:
        event["request"] = _redactar(event["request"])
        if isinstance(event["request"].get("url"), str):
            event["request"]["url"] = _limpiar_url(event["request"]["url"])
        event["request"].pop("query_string", None)

    if "extra" in event:
        event["extra"] = _redactar(event["extra"])

    for exc in event.get("exception", {}).get("values", []):
        if isinstance(exc.get("value"), str):
            exc["value"] = _limpiar_texto(exc["value"])
        for frame in exc.get("stacktrace", {}).get("frames", []):
            if "vars" in frame:
                frame["vars"] = _redactar(frame["vars"])

    _limpiar_breadcrumbs(event)

    return event
