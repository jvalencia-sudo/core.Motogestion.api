"""F0-04: los logs del backend deben ser JSON con fecha/nivel/ruta/taller/usuario
cuando existan (esos últimos tres solo los agrega el middleware de requests, vía
`extra=`) — esto prueba el formatter en sí, sin levantar la app."""
import json
import logging
import sys

from infrastructure.utils.logging_config import JsonFormatter


def _formatear(logger, **extra):
    record = logger.makeRecord(
        logger.name, logging.INFO, __file__, 1, "request", (), None, extra=extra or None
    )
    return json.loads(JsonFormatter().format(record))


def test_incluye_fecha_nivel_logger_y_mensaje():
    logger = logging.getLogger("test.logging_config")
    evento = _formatear(logger)

    assert evento["nivel"] == "INFO"
    assert evento["logger"] == "test.logging_config"
    assert evento["mensaje"] == "request"
    assert "fecha" in evento


def test_incluye_campos_de_la_linea_de_request_cuando_estan_presentes():
    logger = logging.getLogger("test.logging_config")
    evento = _formatear(
        logger, ruta="/api/clientes", metodo="GET", status=200,
        duracion_ms=12.3, taller=1, usuario="sub-123",
    )

    assert evento["ruta"] == "/api/clientes"
    assert evento["metodo"] == "GET"
    assert evento["status"] == 200
    assert evento["taller"] == 1
    assert evento["usuario"] == "sub-123"


def test_omite_campos_opcionales_ausentes():
    logger = logging.getLogger("test.logging_config")
    evento = _formatear(logger)

    for campo in ("ruta", "metodo", "status", "duracion_ms", "taller", "usuario"):
        assert campo not in evento


def test_limpia_detail_de_postgres_del_traceback():
    # El scrub antes solo se aplicaba a lo que se manda a Sentry -- este mensaje
    # salía limpio por logger.error(...) pero el traceback completo (exc_info) se
    # imprimía crudo por stdout/docker logs, con la cédula real en el DETAIL.
    logger = logging.getLogger("test.logging_config")
    try:
        raise ValueError(
            'duplicate key value violates unique constraint "t_pkey"\n'
            "DETAIL:  Key (documento_cli)=(1122334455) already exists."
        )
    except ValueError:
        record = logger.makeRecord(
            logger.name, logging.ERROR, __file__, 1, "Error de base de datos",
            (), sys.exc_info(),
        )
    linea = JsonFormatter().format(record)
    evento = json.loads(linea)

    assert "1122334455" not in linea
    assert "1122334455" not in evento["excepcion"]


def test_limpia_ruta_con_documento_dentro_del_mensaje():
    logger = logging.getLogger("test.logging_config")
    record = logger.makeRecord(
        logger.name, logging.ERROR, __file__, 1,
        "Fallo consultando %s", ("/api/clientes/1122334455",), None,
    )
    evento = json.loads(JsonFormatter().format(record))

    assert "1122334455" not in evento["mensaje"]
    assert evento["mensaje"] == "Fallo consultando /api/clientes/{id}"
