from domain.models.base_model import BaseSchema


class ProductoImpuestoModelo(BaseSchema):
    cod_pro_imp: int = 0
    cod_imp_pro_imp: int
    cod_pro_pro_imp: int
    porcentaje_pro_imp: float
