"""Integración con Wompi (Widget Checkout + verificación de eventos/webhook).

Funciones puras (firmas SHA256). No hace I/O: así se pueden testear sin
llaves reales.
"""
import hashlib
import hmac
from typing import Dict, Optional, Tuple


def firma_integridad(referencia: str, monto_centavos: int, moneda: str, integrity_secret: str) -> str:
    """Firma de integridad del Checkout de Wompi:
    SHA256( referencia + monto_centavos + moneda + integrity_secret )."""
    cadena = f"{referencia}{monto_centavos}{moneda}{integrity_secret}"
    return hashlib.sha256(cadena.encode("utf-8")).hexdigest()


def verificar_evento(payload: Dict, events_secret: str) -> bool:
    """Verifica la firma (checksum) de un evento/webhook de Wompi:
    SHA256( concat(valores de signature.properties) + timestamp + events_secret )."""
    try:
        sig = payload["signature"]
        propiedades = sig["properties"]
        checksum = sig["checksum"]
        timestamp = payload["timestamp"]
        data = payload["data"]
        cadena = ""
        for prop in propiedades:
            valor = data
            for clave in prop.split("."):
                valor = valor[clave]
            cadena += str(valor)
        cadena += str(timestamp) + events_secret
        calculado = hashlib.sha256(cadena.encode("utf-8")).hexdigest()
        # comparación en tiempo constante
        return hmac.compare_digest(calculado, str(checksum))
    except (KeyError, TypeError):
        return False


def leer_transaccion(payload: Dict) -> Optional[Tuple[str, str, str, int]]:
    """Extrae (referencia, estado, transaction_id, monto_en_centavos) del evento
    de transacción. El monto se usa para verificar que coincide con lo que se
    esperaba cobrar antes de activar nada."""
    try:
        tx = payload["data"]["transaction"]
        return (
            tx["reference"],
            tx["status"],
            str(tx.get("id", "")),
            int(tx.get("amount_in_cents", 0) or 0),
        )
    except (KeyError, TypeError):
        return None
