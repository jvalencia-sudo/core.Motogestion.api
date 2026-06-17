from domain.models.base_model import BaseSchema


class ImpuestoModelo(BaseSchema):
    cod_imp: int = 0
    nombre_imp: str
    porcentaje_imp: float
