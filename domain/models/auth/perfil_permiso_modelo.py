from domain.models.base_model import BaseSchema


class PerfilPermisoModelo(BaseSchema):
    cod_prm_pp: int
    cod_prf_pp: int
    cod_est_pp: int


class VwPerfilesPermisosDetalle(BaseSchema):
    cod_prf: int
    nombre_prf: str
    es_admin: bool
    cod_prm: int
    nombre_prm: str
    descripcion_prm: str
    estado_permiso: str
