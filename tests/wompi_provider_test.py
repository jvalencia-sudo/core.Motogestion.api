"""Verificación de eventos/webhook de Wompi: es la puerta de entrada de dinero
real, así que la firma tiene que validarse (y rechazarse) de forma exacta."""
import hashlib

from infrastructure.providers.payments import wompi_provider

EVENTS_SECRET = "test_events_secret"


def _payload_con_checksum_valido(referencia="MG-1-abc123", estado="APPROVED", monto=50000):
    """Arma un payload de Wompi con un checksum calculado igual que Wompi:
    SHA256(concat(valores de las properties) + timestamp + events_secret)."""
    timestamp = 1710000000
    data = {
        "transaction": {
            "id": "tx-1",
            "reference": referencia,
            "status": estado,
            "amount_in_cents": monto,
        }
    }
    propiedades = ["transaction.id", "transaction.status", "transaction.amount_in_cents"]
    cadena = "".join(str(data["transaction"][p.split(".")[1]]) for p in propiedades)
    cadena += str(timestamp) + EVENTS_SECRET
    checksum = hashlib.sha256(cadena.encode("utf-8")).hexdigest()
    return {
        "timestamp": timestamp,
        "data": data,
        "signature": {"properties": propiedades, "checksum": checksum},
    }


def test_verificar_evento_con_firma_valida_pasa():
    payload = _payload_con_checksum_valido()
    assert wompi_provider.verificar_evento(payload, EVENTS_SECRET) is True


def test_verificar_evento_con_checksum_alterado_falla():
    payload = _payload_con_checksum_valido()
    payload["signature"]["checksum"] = "0" * 64
    assert wompi_provider.verificar_evento(payload, EVENTS_SECRET) is False


def test_verificar_evento_con_datos_alterados_despues_de_firmar_falla():
    """Si alguien cambia el monto o el estado después de calculada la firma
    (ej. interceptando el webhook), el checksum ya no cuadra."""
    payload = _payload_con_checksum_valido(monto=50000)
    payload["data"]["transaction"]["amount_in_cents"] = 1  # manipulado
    assert wompi_provider.verificar_evento(payload, EVENTS_SECRET) is False


def test_verificar_evento_con_secret_incorrecto_falla():
    payload = _payload_con_checksum_valido()
    assert wompi_provider.verificar_evento(payload, "otro_secret") is False


def test_verificar_evento_con_payload_incompleto_no_lanza_excepcion():
    """Un payload malformado no debe tumbar el webhook con un 500: debe
    tratarse como firma inválida."""
    assert wompi_provider.verificar_evento({}, EVENTS_SECRET) is False
    assert wompi_provider.verificar_evento({"signature": {}}, EVENTS_SECRET) is False


def test_leer_transaccion_extrae_referencia_estado_y_id():
    payload = _payload_con_checksum_valido(referencia="MG-7-xyz", estado="DECLINED")
    resultado = wompi_provider.leer_transaccion(payload)
    assert resultado == ("MG-7-xyz", "DECLINED", "tx-1")


def test_leer_transaccion_con_payload_invalido_devuelve_none():
    assert wompi_provider.leer_transaccion({}) is None


def test_firma_integridad_es_determinista():
    firma_1 = wompi_provider.firma_integridad("MG-1", 5000000, "COP", "secret")
    firma_2 = wompi_provider.firma_integridad("MG-1", 5000000, "COP", "secret")
    assert firma_1 == firma_2
    assert len(firma_1) == 64  # hex de sha256


def test_firma_integridad_cambia_si_cambia_el_monto():
    firma_1 = wompi_provider.firma_integridad("MG-1", 5000000, "COP", "secret")
    firma_2 = wompi_provider.firma_integridad("MG-1", 5000001, "COP", "secret")
    assert firma_1 != firma_2
