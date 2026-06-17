from domain.models.base_model import BaseSchema
from typing import Optional


class VwClienteModelo(BaseSchema):
    """Mapea la vista vw_clientes básica"""
    documento_cli: str
    nombre_cli: str
    apellido_1_cli: str
    apellido_2_cli: Optional[str] = None
    nombre_completo: str  # Concatenado en la vista
    telefono_cli: str
    correo_cli: str
    direccion_cli: Optional[str] = None


class VwClienteResumenModelo(BaseSchema):
    """Mapea la vista vw_clientes_resumen con total de motos"""
    documento_cli: str
    nombre_completo: str
    telefono_cli: str
    correo_cli: str
    direccion_cli: Optional[str] = None
    total_motos: int
