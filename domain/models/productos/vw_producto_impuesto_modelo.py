from domain.models.base_model import BaseSchema


class VwProductoImpuestoModelo(BaseSchema):
    """Modelo para la vista vw_productos_impuestos"""
    cod_pro_imp: int
    cod_imp_pro_imp: int
    cod_pro_pro_imp: int
    porcentaje_pro_imp: float
    cod_imp: int
    nombre_imp: str
    porcentaje_imp: float
