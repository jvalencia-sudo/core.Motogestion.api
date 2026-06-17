from typing import Optional
from domain.models.base_model import BaseSchema


class UsuarioModelo(BaseSchema):
    documento_usu: str
    nombre_usu: str
    apellido_1_usu: str
    apellido_2_usu: str
    correo_usu: str
    contrasena_usu: str
    cod_tipo_usu: int
    cod_est_usu: int
    sub_id_usu: Optional[str] = None
    cod_prf_usu: int
    cod_rol_prf_usu: int


class VwUsuariosPerfiles(BaseSchema):
    documento_usu: str
    nombre_completo: str
    correo_usu: str
    cod_tipo_usu: int
    estado_usuario: str
    perfil: str
    descripcion_perfil: str
    rol: str
    descripcion_rol: str
