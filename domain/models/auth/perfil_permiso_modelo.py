from domain.models.base_model import BaseSchema


class PerfilPermisoModelo(BaseSchema):
    cod_prm_pp: int
    cod_prf_pp: int
    cod_rol_prf_pp: int
    cod_est_pp: int


class VwPerfilesPermisosDetalle(BaseSchema):
    cod_prf: int
    nombre_prf: str
    nombre_rol: str
    cod_prm: int
    nombre_prm: str
    descripcion_prm: str
    nombre_vis: str
    ruta_vis: str
    estado_permiso: str
