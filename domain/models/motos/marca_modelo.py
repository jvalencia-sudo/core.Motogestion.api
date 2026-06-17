from domain.models.base_model import BaseSchema


class MarcaModelo(BaseSchema):
    cod_mar: int = 0
    nombre_mar: str
