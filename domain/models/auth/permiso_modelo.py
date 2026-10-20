from domain.models.base_model import BaseSchema


class PermisoModelo(BaseSchema):
    cod_prm: int = 0
    nombre_prm: str
    descripcion_prm: str


class VwPermisoModelo(BaseSchema):
    cod_prm: int = 0
    nombre_prm: str
    descripcion_prm: str
