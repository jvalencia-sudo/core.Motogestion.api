from domain.models.base_model import BaseSchema


class ExcepcionModelo(BaseSchema):
    cod_exc: int = 0
    nombre_exc: str
    descripcion_exp: str
