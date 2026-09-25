"""Filtro before_send de Sentry: redacta datos sensibles antes de enviar un evento.

`send_default_pii=False` e `include_local_variables=False` en sentry_sdk.init ya
evitan mandar cookies/headers/IP y variables locales por defecto, pero quedan estos
caminos que ese par de flags no cubre, y que este filtro sí:

1. La URL real de la petición (`event["request"]["url"]`, y la de cada breadcrumb
   HTTP/navegación) trae el documento/placa en el path -- p.ej.
   `/api/clientes/1122334455`. El scrub por clave no alcanza porque es texto, no
   un diccionario con una clave "documento_cli". Se reemplaza cada segmento que
   *parece* un valor real (dígitos largos, NIT con dígito de verificación, o
   alfanumérico tipo placa/pasaporte) por "{id}", y se descarta el query string
   entero.
2. Los errores de Postgres agregan una línea "DETAIL: Key (documento_cli)=(...)
   already exists" con la fila real -- viene en el propio `str(exc)`, así que
   aparece en `event["exception"][...]["value"]` sin importar qué tan poco
   loguee el handler. Se corta esa línea de cualquier texto del evento.
3. `logger.error("...: %s", algo)` hace que la integración de logging de Sentry
   arme `event["logentry"]` con el mensaje ya formateado (`formatted`) y los
   argumentos por separado (`params`) -- ninguno de los dos es `request`/`extra`,
   así que sin este filtro pasarían tal cual.
4. Cualquier ruta que aparezca *dentro* de un texto libre (un mensaje de log, el
   `str()` de una excepción) también se limpia, con la misma lógica de segmentos
   que la URL -- no solo cuando la ruta viaja en su propio campo.
5. El resto (password, documento, tokens, etc.) sigue redactándose por clave en
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
# (4+ dígitos), NIT con dígito de verificación (900123456-7), o alfanumérico tipo
# placa/pasaporte/cédula de extranjería (6-12 caracteres con al menos un dígito).
# El dígito obligatorio en el tercer caso es clave: sin él, palabras de 6-12 letras
# que sí son parte fija de la URL (p.ej. "config" en /talleres/config, "planes" en
# /suscripciones/planes) quedarían redactadas por error -- se comprobó con un test
# que fallaba así. Ningún segmento fijo real de las rutas del API tiene dígitos
# (se revisó la lista completa de endpoints), así que ampliar el rango no crea
# falsos positivos nuevos.
_SEGMENTO_VALOR = re.compile(
    r"^\d{4,}$|^\d+-\d+$|^(?=[A-Za-z0-9]*\d)[A-Za-z0-9]{6,12}$"
)

# Postgres agrega esta línea a los mensajes de restricción con la fila real que
# las violó (p.ej. "DETAIL:  Key (documento_cli)=(1122334455) already exists.").
_DETAIL_LINEA = re.compile(r"(?im)^\s*DETAIL:.*$")

# Ruta tipo "/api/clientes/1122334455" dentro de un texto libre (mensaje de log,
# str() de una excepción) -- mismo tratamiento que _limpiar_url pero sin depender
# de que el valor viaje en su propio campo `url`.
_RUTA_EN_TEXTO = re.compile(r"/[\w{}/-]+")


def _limpiar_segmentos(ruta: str) -> str:
    segmentos = ["{id}" if _SEGMENTO_VALOR.match(s) else s for s in ruta.split("/")]
    return "/".join(segmentos)


def _limpiar_url(url: str) -> str:
    try:
        partes = urlsplit(url)
    except ValueError:
        return url
    # El query string también puede llevar valores (?documento=...): se descarta
    # entero en vez de intentar filtrar parámetro por parámetro.
    return urlunsplit(
        (partes.scheme, partes.netloc, _limpiar_segmentos(partes.path), "", partes.fragment)
    )


def limpiar_texto(valor: str) -> str:
    """Corta líneas DETAIL de Postgres y reemplaza rutas con valores reales por
    "{id}" en cualquier texto libre. Pública porque también la usa
    infrastructure.utils.logging_config.JsonFormatter -- es la misma regla para
    lo que sale a Sentry y lo que sale por stdout/docker logs, no dos scrubs
    separados que puedan divergir."""
    valor = _DETAIL_LINEA.sub("[DETAIL REDACTADO]", valor)
    return _RUTA_EN_TEXTO.sub(lambda m: _limpiar_segmentos(m.group(0)), valor)


def _redactar(valor: Any) -> Any:
    if isinstance(valor, dict):
        return {
            k: "[REDACTADO]" if k.lower() in _CLAVES_SENSIBLES else _redactar(v)
            for k, v in valor.items()
        }
    if isinstance(valor, list):
        return [_redactar(v) for v in valor]
    if isinstance(valor, str):
        return limpiar_texto(valor)
    return valor


def _limpiar_breadcrumbs(event: dict) -> None:
    for crumb in event.get("breadcrumbs", {}).get("values", []):
        data = crumb.get("data")
        if isinstance(data, dict) and isinstance(data.get("url"), str):
            data["url"] = _limpiar_url(data["url"])
        if isinstance(crumb.get("message"), str):
            crumb["message"] = limpiar_texto(crumb["message"])


def _limpiar_logentry(event: dict) -> None:
    # logger.error("...: %s", algo) hace que la integración de logging arme este
    # campo con el mensaje ya formateado y los argumentos por separado -- ninguno
    # de los dos pasa por _redactar(request/extra), así que se limpian aparte.
    logentry = event.get("logentry")
    if not isinstance(logentry, dict):
        return
    for campo in ("message", "formatted"):
        if isinstance(logentry.get(campo), str):
            logentry[campo] = limpiar_texto(logentry[campo])
    if isinstance(logentry.get("params"), list):
        logentry["params"] = [
            limpiar_texto(p) if isinstance(p, str) else p for p in logentry["params"]
        ]


def scrub_before_send(event: dict, hint: dict) -> dict:
    if "request" in event:
        event["request"] = _redactar(event["request"])
        if isinstance(event["request"].get("url"), str):
            event["request"]["url"] = _limpiar_url(event["request"]["url"])
        event["request"].pop("query_string", None)

    if "extra" in event:
        event["extra"] = _redactar(event["extra"])

    _limpiar_logentry(event)

    for exc in event.get("exception", {}).get("values", []):
        if isinstance(exc.get("value"), str):
            exc["value"] = limpiar_texto(exc["value"])
        for frame in exc.get("stacktrace", {}).get("frames", []):
            if "vars" in frame:
                frame["vars"] = _redactar(frame["vars"])

    _limpiar_breadcrumbs(event)

    return event
