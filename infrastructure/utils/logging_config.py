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

# Campos opcionales que solo trae la línea resumen de cada request (ver
# infrastructure/middleware/request_logging.py). El resto de los logs de la app no
# los tiene, y no deben aparecer en esas líneas.
_CAMPOS_OPCIONALES = ("ruta", "metodo", "status", "duracion_ms", "taller", "usuario")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        evento = {
            "fecha": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "nivel": record.levelname,
            "logger": record.name,
            "mensaje": record.getMessage(),
        }
        for campo in _CAMPOS_OPCIONALES:
            valor = getattr(record, campo, None)
            if valor is not None:
                evento[campo] = valor
        if record.exc_info:
            evento["excepcion"] = self.formatException(record.exc_info)
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
