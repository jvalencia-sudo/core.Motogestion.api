"""Integración con Wompi (Web Checkout + verificación de eventos/webhook).

Funciones puras (firmas SHA256) + armado de la URL de checkout. No hace I/O:
así se pueden testear sin llaves reales.
"""
import hashlib
import hmac
from typing import Dict, Optional, Tuple
from urllib.parse import urlencode


def firma_integridad(referencia: str, monto_centavos: int, moneda: str, integrity_secret: str) -> str:
    """Firma de integridad del Web Checkout de Wompi:
    SHA256( referencia + monto_centavos + moneda + integrity_secret )."""
    cadena = f"{referencia}{monto_centavos}{moneda}{integrity_secret}"
    return hashlib.sha256(cadena.encode("utf-8")).hexdigest()


def construir_url_checkout(
    checkout_url: str,
    public_key: str,
    integrity_secret: str,
    referencia: str,
    monto_centavos: int,
    redirect_url: str,
    moneda: str = "COP",
) -> str:
    """URL del Web Checkout de Wompi para redirigir al usuario a pagar."""
    firma = firma_integridad(referencia, monto_centavos, moneda, integrity_secret)
    params = {
        "public-key": public_key,
        "currency": moneda,
        "amount-in-cents": monto_centavos,
        "reference": referencia,
        "redirect-url": redirect_url,
        "signature:integrity": firma,
    }
    return f"{checkout_url}?{urlencode(params)}"


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


def leer_transaccion(payload: Dict) -> Optional[Tuple[str, str, str]]:
    """Extrae (referencia, estado, transaction_id) del evento de transacción."""
    try:
        tx = payload["data"]["transaction"]
        return tx["reference"], tx["status"], str(tx.get("id", ""))
    except (KeyError, TypeError):
        return None
