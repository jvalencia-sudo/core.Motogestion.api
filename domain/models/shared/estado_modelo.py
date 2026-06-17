from domain.models.base_model import BaseSchema


class EstadoModelo(BaseSchema):
    cod_est: int = 0
    nombre_est: str
