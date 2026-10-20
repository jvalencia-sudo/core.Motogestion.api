from typing import Dict, List

from domain.models.auth.permiso_modelo import PermisoModelo, VwPermisoModelo
from domain.services.base_service import BaseService
from repository.auth.permiso_repositorio import PermisoRepositorio


class PermisoServicio(BaseService[PermisoModelo, PermisoRepositorio]):
    def __init__(self):
        super().__init__(PermisoRepositorio())

    def __parse__(self, record: Dict) -> PermisoModelo:
        return PermisoModelo.model_validate(record)

    async def obtener_permisos_por_perfil(self, cod_prf: int) -> List[PermisoModelo]:
        permisos = await self.repository.obtener_permisos_por_perfil(cod_prf)
        return self.__parse_all__(permisos)

    async def obtener_vw_permisos(self) -> List[VwPermisoModelo]:
        registros = await self.repository.obtener_vw_permisos()
        return self.__parse_all_custom__(registros, VwPermisoModelo)
