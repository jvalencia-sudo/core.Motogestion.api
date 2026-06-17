from domain.models.base_model import BaseSchema


class PermisoModelo(BaseSchema):
    cod_prm:int = 0
    nombre_prm:str
    descripcion_prm:str
    ruta_vis_prm:str

class VwPermisoModelo(BaseSchema):
    cod_prm:int = 0
    nombre_prm:str
    descripcion_prm:str
    nombre_est_prm:str
    ruta_vis_prm:str
    nombre_rol_prf_prm:int
