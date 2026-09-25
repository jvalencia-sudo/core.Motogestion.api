"""Logs estructurados en JSON (una línea por evento).

F0-04 pide que los logs del backend tengan fecha, nivel, ruta, taller y usuario.
Los tres últimos solo los pone infrastructure/middleware/request_logging.py (vía
`extra=`) en la línea resumen de cada request; el resto de los `logger.info/warning/
error` de la app siguen funcionando igual, solo que ahora en JSON en vez de texto
plano.
"""
import json
import logging
from datetime import datetime, timezone

from infrastructure.utils.sentry_scrub import limpiar_texto

# Campos opcionales que solo trae la línea resumen de cada request (ver
# infrastructure/middleware/request_logging.py). El resto de los logs de la app no
# los tiene, y no deben aparecer en esas líneas.
_CAMPOS_OPCIONALES = ("ruta", "metodo", "status", "duracion_ms", "taller", "usuario")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        # Misma limpieza que antes de mandar un evento a Sentry (DETAIL de Postgres,
        # rutas con documento/placa reales) -- sin esto, un logger.error(exc_info=...)
        # sacaba esos datos limpios por Sentry pero crudos por stdout/docker logs.
        evento = {
            "fecha": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "nivel": record.levelname,
            "logger": record.name,
            "mensaje": limpiar_texto(record.getMessage()),
        }
        for campo in _CAMPOS_OPCIONALES:
            valor = getattr(record, campo, None)
            if valor is not None:
                evento[campo] = valor
        if record.exc_info:
            evento["excepcion"] = limpiar_texto(self.formatException(record.exc_info))
        # default=str: por si algún día se loguea un valor no serializable (Decimal,
        # datetime sin tz, etc.) — mejor un str feo que romper el logging.
        return json.dumps(evento, ensure_ascii=False, default=str)


def configurar_logging(nivel: int = logging.INFO) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(nivel)
