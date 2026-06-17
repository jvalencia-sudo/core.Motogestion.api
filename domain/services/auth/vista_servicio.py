from typing import Dict, List

from domain.models.auth.perfil_modelo import PerfilModelo
from domain.models.auth.permiso_modelo import PermisoModelo
from domain.models.auth.vista_modelo import VistaModelo
from domain.services.base_service import BaseService
from repository.base_repository import BaseRepository


class VistaServicio(BaseService[VistaModelo,None]):
    def __init__(self):
        super().__init__(BaseRepository("auth", "vistas", "cod_vis"))

    def __parse__(self, record: Dict) -> VistaModelo:
        normalized = self.__normalize_keys__(record)
        return VistaModelo.model_validate(normalized)



