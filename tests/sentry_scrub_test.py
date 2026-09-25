"""F0-04: antes de mandar nada a Sentry, hay que redactar datos sensibles del
evento (request/extra/locals de los frames) — esto prueba solo la función de
redacción en sí (sin BD, sin red)."""
from infrastructure.utils.sentry_scrub import scrub_before_send


def test_redacta_claves_sensibles_en_request():
    event = {
        "request": {
            "headers": {"Authorization": "Bearer secreto", "User-Agent": "x"},
            "data": {"password": "1234", "email": "a@b.com"},
        }
    }

    resultado = scrub_before_send(event, {})

    assert resultado["request"]["headers"]["Authorization"] == "[REDACTADO]"
    assert resultado["request"]["headers"]["User-Agent"] == "x"
    assert resultado["request"]["data"]["password"] == "[REDACTADO]"
    assert resultado["request"]["data"]["email"] == "a@b.com"


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
