from datetime import date, datetime
from typing import Optional

from domain.models.base_model import BaseSchema


class TallerModel(BaseSchema):
    cod_taller: int
    nombre_tal: str
    nit_tal: Optional[str] = None
    correo_tal: Optional[str] = None
    telefono_tal: Optional[str] = None
    estado_tal: Optional[str] = None          # prueba | activo | suspendido
    plan_tal: Optional[str] = None
    fecha_creacion_tal: Optional[datetime] = None
    fecha_fin_susc_tal: Optional[date] = None
    modo_mano_obra: Optional[str] = None       # HORAS | LIBRE
    tarifa_hora_pred: Optional[int] = None
    direccion_tal: Optional[str] = None
    texto_pie_comprobante: Optional[str] = None
    dias_garantia_pred: Optional[int] = None
