from datetime import date
from typing import Optional
from domain.models.base_model import BaseSchema


class ReclamoModelo(BaseSchema):
    cod_rec: int = 0
    descripcion_rec: str
    consecutivo_ot_rec: int


class VwReclamosCompleto(BaseSchema):
    """Modelo para vista completa de reclamos con toda la información relacionada"""
    cod_rec: int
    descripcion_rec: str
    consecutivo_ot_rec: int

    # Información de la OT
    fecha_elaboracion_ot: date
    fecha_entrega_ot: Optional[date] = None
    kilometraje_ingreso_ot: int
    observacion_cli_ot: Optional[str] = None
    observacion_ot: Optional[str] = None
    fecha_fin_garantia_ot: Optional[date] = None
    estado_ot: str

    # Información de la moto
    placa_mot: str
    modelo_mot: int
    color_mot: str
    cilindraje_mot: int
    marca_moto: str
    moto_completa: str

    # Información del cliente
    documento_cli: str
    nombre_completo_cliente: str
    telefono_cli: str
    correo_cli: str
    direccion_cli: Optional[str] = None

    # Información de usuarios responsables
    documento_recepcionista: str
    recepcionista: str
    documento_mecanico: str
    mecanico: str

    # Información de garantía
    estado_garantia: str
    dias_garantia_restantes: Optional[int] = None


class VwReclamosDetalle(BaseSchema):
    cod_rec: int
    descripcion_rec: str
    consecutivo_ot: int
    fecha_elaboracion_ot: date
    fecha_entrega_ot: Optional[date] = None
    placa_mot: str
    cliente: str
    telefono_cli: str
    estado_ot: str
