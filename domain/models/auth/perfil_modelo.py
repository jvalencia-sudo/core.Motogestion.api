from domain.models.base_model import BaseSchema


class PerfilModelo(BaseSchema):
    cod_prf: int = 0
    nombre_prf: str
    descripcion_prf: str
    cod_est_prf: int
    es_admin: bool = False


class VwPerfilModelo(BaseSchema):
    cod_prf: int = 0
    nombre_prf: str
    descripcion_prf: str
    nombre_est_prf: str
    es_admin: bool = False
