from domain.models.base_model import BaseSchema
from typing import Optional


class VwMarcaModelo(BaseSchema):
    """Mapea la vista vw_marcas básica"""
    cod_mar: int
    nombre_mar: str


class VwMarcaResumenModelo(BaseSchema):
    """Mapea la vista vw_marcas_resumen con total de motos"""
    cod_mar: int
    nombre_mar: str
    total_motos: int


class VwMarcaMotosModelo(BaseSchema):
    """Mapea la vista vw_marcas_motos con detalle de motos por marca"""
    cod_mar: int
    nombre_mar: str
    placa_mot: Optional[str] = None
    modelo_mot: Optional[int] = None
    color_mot: Optional[str] = None
    cilindraje_mot: Optional[int] = None
