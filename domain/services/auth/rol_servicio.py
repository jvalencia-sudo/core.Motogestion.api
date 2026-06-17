from typing import Dict, List

from domain.models.auth.perfil_modelo import PerfilModelo
from domain.models.auth.permiso_modelo import PermisoModelo
from domain.models.auth.rol_modelo import RolModelo
from domain.services.base_service import BaseService
from repository.base_repository import BaseRepository


class RolServicio(BaseService[RolModelo,None]):
    def __init__(self):
        super().__init__(BaseRepository("auth", "roles", "cod_rol"))

    def __parse__(self, record: Dict) -> RolModelo:
        normalized = self.__normalize_keys__(record)
        return RolModelo.model_validate(normalized)


