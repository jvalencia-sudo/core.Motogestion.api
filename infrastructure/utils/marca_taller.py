from dataclasses import dataclass
from typing import Optional


@dataclass
class ConfigMarcaTaller:
    """Personalización visual de la orden (F1-09): la misma estructura la usa
    tanto la generación real (datos guardados del taller) como la vista
    previa (datos del formulario, sin guardar)."""
    nombre_comercial: Optional[str] = None
    logo_bytes: Optional[bytes] = None
    color_principal: str = "#00B06E"
    texto_condiciones: Optional[str] = None
    texto_pie: Optional[str] = None
    mostrar_precios_unitarios: bool = True
    mostrar_mecanico: bool = True
    mostrar_firma_cliente: bool = False
