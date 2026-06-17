from domain.models.base_model import BaseSchema
from typing import Optional


class VwMotoModelo(BaseSchema):
    """Mapea la vista vw_motos básica"""
    placa_mot: str
    modelo_mot: int
    color_mot: str
    cilindraje_mot: int
    documento_cli_mot: str
    cod_marca_mot: int


class VwMotoMarcasModelo(BaseSchema):
    """Mapea la vista vw_motos_marcas con información de marca"""
    placa_mot: str
    modelo_mot: int
    color_mot: str
    cilindraje_mot: int
    documento_cli_mot: str
    cod_marca_mot: int
    marca: str


class VwMotoDetalleModelo(BaseSchema):
    """Mapea la vista vw_motos_detalle con información completa de marca y cliente"""
    placa_mot: str
    modelo_mot: int
    color_mot: str
    cilindraje_mot: int
    marca: str
    documento_cli: str  # documento del cliente
    nombre_completo_cliente: str
    telefono_cli: str
    correo_cli: str
