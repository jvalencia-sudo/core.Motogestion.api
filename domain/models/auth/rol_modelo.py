

from domain.models.base_model import BaseSchema


class RolModelo(BaseSchema):
    cod_rol: int = 0
    nombre_rol: str
    descripcion_rol: str


