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
