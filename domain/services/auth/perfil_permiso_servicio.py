from typing import Dict, List

from starlette.status import HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND

from domain.contracts.auth.perfil_permiso_contract import (
    AsignarPermisoContract,
    CambiarEstadoPermisoContract,
    PermisoDisponibleContract,
    PermisoAsignadoContract,
    ReemplazarPermisosContract,
)
from domain.models.auth.perfil_permiso_modelo import PerfilPermisoModelo, VwPerfilesPermisosDetalle
from domain.services.base_service import BaseService
from infrastructure.exceptions.domain_exception import DomainException
from repository.auth.perfil_permiso_repositorio import PerfilPermisoRepositorio
from repository.auth.permiso_repositorio import PermisoRepositorio
from repository.auth.perfil_repositorio import PerfilRepositorio

ADMIN_ROL = 1


class PerfilPermisoServicio(BaseService[PerfilPermisoModelo, PerfilPermisoRepositorio]):
    def __init__(self):
        super().__init__(PerfilPermisoRepositorio())
        # Los permisos (catálogo) los provee su repo dueño.
        self.permiso_repo = PermisoRepositorio()
        self.perfil_repo = PerfilRepositorio()

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
        """Permisos que NO están asignados al perfil. Se orquesta: catálogo completo
        (repo de permisos) menos los ya asignados (repo de perfiles_permisos)."""
        todos = await self.permiso_repo.obtener_vw_permisos()
        asignados = await self.repository.obtener_cod_prm_asignados(cod_prf, cod_rol)
        ids_asignados = {a.get("COD_PRM_PP") for a in asignados}
        disponibles = [p for p in todos if p.get("COD_PRM") not in ids_asignados]
        disponibles.sort(key=lambda p: (p.get("NOMBRE_PRM") or ""))
        return self.__parse_all_custom__(disponibles, PermisoDisponibleContract)

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

    async def reemplazar_permisos(
        self, cod_prf: int, contract: ReemplazarPermisosContract, usuario: str
    ) -> dict:
        """Reemplaza de una vez todos los permisos de un perfil (matriz de F0-13).
        Rechaza el perfil Administrador (ya tiene acceso a todo, no se edita) y
        perfiles de otro taller (RLS: verificar_perfil_existe no los ve)."""
        perfil = await self.perfil_repo.verificar_perfil_existe(cod_prf)
        if not perfil:
            raise DomainException(
                "Perfil no encontrado. Recarga la página y vuelve a intentar.", HTTP_404_NOT_FOUND
            )

        cod_rol = perfil.get("COD_ROL_PRF")
        if cod_rol == ADMIN_ROL:
            raise DomainException(
                "El rol Administrador no se puede editar: ya tiene acceso a todo. Si "
                "necesitas un rol con menos permisos, crea uno nuevo.",
                HTTP_400_BAD_REQUEST,
            )

        await self.repository.reemplazar_permisos(
            cod_prf, cod_rol, contract.cod_prm_list, usuario
        )
        return {"success": True, "message": "Permisos actualizados correctamente"}

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

