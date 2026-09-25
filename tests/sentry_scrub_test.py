"""F0-04: antes de mandar nada a Sentry, hay que redactar datos sensibles del
evento (request/extra/locals de los frames) — esto prueba solo la función de
redacción en sí (sin BD, sin red)."""
from infrastructure.utils.sentry_scrub import scrub_before_send


def test_redacta_claves_sensibles_en_request():
    event = {
        "request": {
            "headers": {"Authorization": "Bearer secreto", "User-Agent": "x"},
            "data": {"password": "1234", "email": "a@b.com", "otro": "valor"},
        }
    }

    resultado = scrub_before_send(event, {})

    assert resultado["request"]["headers"]["Authorization"] == "[REDACTADO]"
    assert resultado["request"]["headers"]["User-Agent"] == "x"
    assert resultado["request"]["data"]["password"] == "[REDACTADO]"
    assert resultado["request"]["data"]["email"] == "[REDACTADO]"
    assert resultado["request"]["data"]["otro"] == "valor"


def test_limpia_documento_de_la_url_del_request():
    event = {"request": {"url": "https://api.example.com/api/clientes/1122334455?x=1"}}

    resultado = scrub_before_send(event, {})

    url = resultado["request"]["url"]
    assert "1122334455" not in url
    assert url == "https://api.example.com/api/clientes/{id}"


def test_limpia_placa_de_la_url_del_request():
    event = {"request": {"url": "https://api.example.com/api/motos/ABC123"}}

    resultado = scrub_before_send(event, {})

    assert resultado["request"]["url"] == "https://api.example.com/api/motos/{id}"


def test_no_confunde_un_segmento_fijo_de_6_letras_con_una_placa():
    # /talleres/config y /suscripciones/planes son rutas reales -- sin exigir un
    # dígito en el heurístico de "parece una placa", quedaban redactadas por error.
    event = {"request": {"url": "https://api.example.com/api/talleres/config"}}

    resultado = scrub_before_send(event, {})

    assert resultado["request"]["url"] == "https://api.example.com/api/talleres/config"


def test_limpia_url_de_un_breadcrumb():
    event = {
        "breadcrumbs": {
            "values": [
                {
                    "category": "http",
                    "data": {"url": "https://api.example.com/api/clientes/1122334455"},
                }
            ]
        }
    }

    resultado = scrub_before_send(event, {})

    url = resultado["breadcrumbs"]["values"][0]["data"]["url"]
    assert "1122334455" not in url


def test_limpia_detail_del_mensaje_de_excepcion_de_postgres():
    event = {
        "exception": {
            "values": [
                {
                    "value": (
                        'duplicate key value violates unique constraint "t_pkey"\n'
                        "DETAIL:  Key (documento_cli)=(1122334455) already exists."
                    )
                }
            ]
        }
    }

    resultado = scrub_before_send(event, {})

    valor = resultado["exception"]["values"][0]["value"]
    assert "1122334455" not in valor
    assert "duplicate key value violates unique constraint" in valor


def test_redacta_claves_sensibles_en_extra():
    event = {"extra": {"documento_cli": "12345678", "otro": "valor"}}

    resultado = scrub_before_send(event, {})

    assert resultado["extra"]["documento_cli"] == "[REDACTADO]"
    assert resultado["extra"]["otro"] == "valor"


def test_redacta_locals_en_los_frames_del_stack():
    event = {
        "exception": {
            "values": [
                {
                    "stacktrace": {
                        "frames": [
                            {"vars": {"contrasena_usu": "abc", "x": 1}},
                            {"vars": {"documento_cli_mot": "999", "y": 2}},
                        ]
                    }
                }
            ]
        }
    }

    resultado = scrub_before_send(event, {})

    frames = resultado["exception"]["values"][0]["stacktrace"]["frames"]
    assert frames[0]["vars"]["contrasena_usu"] == "[REDACTADO]"
    assert frames[0]["vars"]["x"] == 1
    assert frames[1]["vars"]["documento_cli_mot"] == "[REDACTADO]"
    assert frames[1]["vars"]["y"] == 2


def test_no_falla_con_evento_vacio():
    assert scrub_before_send({}, {}) == {}


def test_limpia_nit_con_digito_de_verificacion_en_la_url():
    # NIT de empresa (flotas de mensajería/domicilios que se registran como
    # clientes) -- formato "900123456-7", que el heurístico de placa no cubría.
    event = {"request": {"url": "https://api.example.com/api/clientes/900123456-7"}}

    resultado = scrub_before_send(event, {})

    url = resultado["request"]["url"]
    assert "900123456-7" not in url
    assert url == "https://api.example.com/api/clientes/{id}"


def test_limpia_documento_tipo_pasaporte_o_cedula_extranjeria():
    # Documentos de 9 caracteres alfanuméricos (pasaporte, cédula de extranjería)
    # quedaban fuera del rango fijo de 6 caracteres del heurístico anterior.
    event = {"request": {"url": "https://api.example.com/api/clientes/AB1234567"}}

    resultado = scrub_before_send(event, {})

    assert resultado["request"]["url"] == "https://api.example.com/api/clientes/{id}"


def test_limpia_logentry_formatted_y_params():
    # logger.error("...: %s", algo) hace que la integración de logging de Sentry
    # arme event["logentry"] con el mensaje formateado y los argumentos por
    # separado -- ninguno pasa por request/extra, así que scrub_before_send debe
    # limpiarlos aparte.
    event = {
        "logentry": {
            "message": "Otro fallo %s",
            "formatted": "Otro fallo /api/clientes/900123456-7",
            "params": ["/api/clientes/900123456-7"],
        }
    }

    resultado = scrub_before_send(event, {})

    logentry = resultado["logentry"]
    assert "900123456-7" not in logentry["formatted"]
    assert logentry["formatted"] == "Otro fallo /api/clientes/{id}"
    assert logentry["params"] == ["/api/clientes/{id}"]


def test_limpia_detail_dentro_de_logentry_message():
    event = {
        "logentry": {
            "message": (
                'duplicate key value violates unique constraint "t_pkey"\n'
                "DETAIL:  Key (documento_cli)=(1122334455) already exists."
            ),
        }
    }

    resultado = scrub_before_send(event, {})

    assert "1122334455" not in resultado["logentry"]["message"]
