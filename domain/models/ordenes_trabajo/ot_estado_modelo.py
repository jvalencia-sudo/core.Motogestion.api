from typing import Optional
from domain.models.base_model import BaseSchema


class OtEstadoModelo(BaseSchema):
    cod_ot_est: int = 0
    nombre_ot_est: str
