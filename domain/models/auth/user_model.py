from typing import List, Optional
from datetime import datetime

from pydantic import BaseModel

from domain.models.base_model import BaseSchema



class UserModel(BaseSchema):
    documento_usu: int = 0
    nombre_usu: str
    apellido_1_usu: str
    apellido_2_usu: Optional[str] = None
    correo_usu: Optional[str] = None
    contrasena_usu: Optional[str] = None
    cod_est_usu: Optional[int] = 1
    cod_tipo_usu: Optional[int] = 1
    sub_id_usu: str
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



class UserWithPermissionsModel(UserModel):
    permissions: Optional[List[str]]


class UserPermissionsModel(BaseModel):
    user_id: str
    permissions: Optional[List[str]]
