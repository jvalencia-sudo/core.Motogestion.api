import re


def normalizar_placa(placa: str) -> str:
    """Mayúsculas y sin caracteres no alfanuméricos: 'abc 12d', 'ABC-12D' y
    'ABC12D' deben resolver a la misma moto, tanto al guardar como al buscar."""
    return re.sub(r"[^A-Za-z0-9]", "", placa).upper()
