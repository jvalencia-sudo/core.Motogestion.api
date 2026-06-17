from typing import Dict, List

from domain.contracts.auth.perfil_permiso_contract import (
    AsignarPermisoContract,
    CambiarEstadoPermisoContract,
    PermisoDisponibleContract,
    PermisoAsignadoContract
)
from domain.models.auth.perfil_permiso_modelo import PerfilPermisoModelo, VwPerfilesPermisosDetalle
from domain.services.base_service import BaseService
from repository.auth.perfil_permiso_repositorio import PerfilPermisoRepositorio


class PerfilPermisoServicio(BaseService[PerfilPermisoModelo, PerfilPermisoRepositorio]):
    def __init__(self):
        super().__init__(PerfilPermisoRepositorio())

    def __parse__(self, record: Dict) -> PerfilPermisoModelo:
        return PerfilPermisoModelo.model_validate(record)

    async def obtener_vw_perfiles_permisos_detalle(self) -> List[VwPerfilesPermisosDetalle]:
        """Obtiene todos los perfiles con sus permisos"""
        registros = await self.repository.obtener_vw_perfiles_permisos_detalle()
        return self.__parse_all_custom__(registros, VwPerfilesPermisosDetalle)

    async def obtener_permisos_por_perfil(self, cod_prf: int, cod_rol: int) -> List[PermisoAsignadoContract]:
        """Obtiene todos los permisos asignados a un perfil específico"""
        registros = await self.repository.obtener_permisos_por_perfil(cod_prf, cod_rol)
        return self.__parse_all_custom__(registros, PermisoAsignadoContract)

    async def obtener_permisos_disponibles(self, cod_prf: int, cod_rol: int) -> List[PermisoDisponibleContract]:
        """Obtiene permisos que NO están asignados al perfil"""
        registros = await self.repository.obtener_permisos_disponibles(cod_prf, cod_rol)
        return self.__parse_all_custom__(registros, PermisoDisponibleContract)

    async def asignar_permiso(self, contract: AsignarPermisoContract) -> dict:
        """Asigna un nuevo permiso a un perfil"""
        # Verificar si el permiso ya existe
        existe = await self.repository.verificar_permiso_existe(
            contract.cod_prf,
            contract.cod_rol,
            contract.cod_prm
        )

        if existe:
            return {
                "success": False,
                "message": "El permiso ya está asignado a este perfil"
            }

        # Crear el modelo para insertar
        modelo = PerfilPermisoModelo(
            cod_prm_pp=contract.cod_prm,
            cod_prf_pp=contract.cod_prf,
            cod_rol_prf_pp=contract.cod_rol,
            cod_est_pp=contract.cod_est
        )

        await self.repository.create(modelo)

        return {
            "success": True,
            "message": "Permiso asignado correctamente"
        }

    async def cambiar_estado_permiso(self, contract: CambiarEstadoPermisoContract) -> dict:
        """Activa o desactiva un permiso de un perfil"""
        # Verificar que el permiso exista
        existe = await self.repository.verificar_permiso_existe(
            contract.cod_prf,
            contract.cod_rol,
            contract.cod_prm
        )

        if not existe:
            return {
                "success": False,
                "message": "El permiso no está asignado a este perfil"
            }

        await self.repository.actualizar_estado_permiso(
            contract.cod_prf,
            contract.cod_rol,
            contract.cod_prm,
            contract.cod_est
        )

        estado_texto = "activado" if contract.cod_est == 1 else "desactivado"
        return {
            "success": True,
            "message": f"Permiso {estado_texto} correctamente"
        }

