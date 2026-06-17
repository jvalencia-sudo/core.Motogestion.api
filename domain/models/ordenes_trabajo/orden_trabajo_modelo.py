from datetime import date
from typing import Optional
from domain.models.base_model import BaseSchema


class OrdenTrabajoModelo(BaseSchema):
    consecutivo_ot: int = 0
    fecha_elaboracion_ot: date
    fecha_entrega_ot: Optional[date] = None
    kilometraje_ingreso_ot: int
    kilometreje_salida_ot: Optional[int] = None
    observacion_cli_ot: Optional[str] = None
    observacion_ot: Optional[str] = None
    placa_mot_ot: str
    documento_usu_rp_ot: str
    documento_usu_mc_ot: str
    cod_ot_est_ot: int
    fecha_fin_garantia_ot: Optional[date] = None


class VwOrdenesTrabajoCompleta(BaseSchema):
    consecutivo_ot: int
    fecha_elaboracion_ot: date
    fecha_entrega_ot: Optional[date] = None
    kilometraje_ingreso_ot: int
    observacion_cli_ot: Optional[str] = None
    observacion_ot: Optional[str] = None
    fecha_fin_garantia_ot: Optional[date] = None
    placa_mot: str
    modelo_mot: int
    color_mot: str
    cilindraje_mot: int
    marca_moto: str
    documento_cli: str
    nombre_completo_cliente: str
    telefono_cli: str
    correo_cli: str
    direccion_cli: Optional[str] = None
    documento_recepcionista: str
    recepcionista: str
    documento_mecanico: str
    mecanico: str
    estado_ot: str
    cod_ot_est_ot: int


class VwResumenFinancieroOt(BaseSchema):
    consecutivo_ot: int
    fecha_elaboracion_ot: date
    cliente: str
    placa_mot: str
    total_items: int
    subtotal_productos: float
    total_impuestos: float
    total_ot: float


class VwOtPendientes(BaseSchema):
    consecutivo_ot: int
    fecha_elaboracion_ot: date
    dias_pendiente: int
    cliente: str
    telefono_cli: str
    placa_mot: str
    moto: str
    mecanico_asignado: str
    estado: str


class OrdenAnteriorModelo(BaseSchema):
    """Modelo para la orden anterior con datos de garantía"""
    fecha_fin_garantia_ot: Optional[date] = None
    fecha_entrega_ot: Optional[date] = None
