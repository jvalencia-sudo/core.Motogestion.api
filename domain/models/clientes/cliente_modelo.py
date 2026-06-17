from domain.models.base_model import BaseSchema
from typing import Optional


class ClienteModelo(BaseSchema):
    documento_cli: str
    nombre_cli: str
    apellido_1_cli: str
    apellido_2_cli: Optional[str] = None
    telefono_cli: str
    correo_cli: str
    direccion_cli: Optional[str] = None


class VwClientesMotos(BaseSchema):
    documento_cli: str
    nombre_completo: str
    telefono_cli: str
    correo_cli: str
    direccion_cli: str
    placa_mot: str
    modelo_mot: str
    color_mot: str
    cilindraje_mot: int
    marca: str
