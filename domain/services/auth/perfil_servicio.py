from typing import Dict, List

from domain.contracts.auth.perfil_contract import (
    CrearPerfilContract,
    ActualizarPerfilContract,
    CambiarEstadoPerfilContract,
    PerfilDetalleContract
)
from domain.models.auth.perfil_modelo import PerfilModelo, VwPerfilModelo
from domain.services.base_service import BaseService
from repository.auth.perfil_repositorio import PerfilRepositorio


class PerfilServicio(BaseService[PerfilModelo, PerfilRepositorio]):
    def __init__(self):
        super().__init__(PerfilRepositorio())

    def __parse__(self, record: Dict) -> PerfilModelo:
        normalized = self.__normalize_keys__(record)
        return PerfilModelo.model_validate(normalized)

    async def obtener_vw_perfiles(self) -> List[PerfilDetalleContract]:
        """Obtiene todos los perfiles con información completa desde la vista"""
        registros = await self.repository.obtener_vw_perfiles()
        return self.__parse_all_custom__(registros, PerfilDetalleContract)

    async def crear_perfil(self, contract: CrearPerfilContract) -> dict:
        """Crea un nuevo perfil"""
        modelo = PerfilModelo(
            cod_prf=0,  # Se generará automáticamente
            nombre_prf=contract.nombre_prf,
            descripcion_prf=contract.descripcion_prf,
            cod_rol_prf=contract.cod_rol_prf,
            cod_est_prf=contract.cod_est_prf
        )

        cod_prf = await self.repository.create(modelo)

        return {
            "success": True,
            "message": "Perfil creado correctamente",
            "cod_prf": cod_prf
        }

    async def actualizar_perfil(self, contract: ActualizarPerfilContract) -> dict:
        """Actualiza un perfil existente"""
        # Verificar que el perfil existe
        existe = await self.repository.verificar_perfil_existe(contract.cod_prf)

        if not existe:
            return {
                "success": False,
                "message": "El perfil no existe"
            }

        modelo = PerfilModelo(
            cod_prf=contract.cod_prf,
            nombre_prf=contract.nombre_prf,
            descripcion_prf=contract.descripcion_prf,
            cod_rol_prf=contract.cod_rol_prf,
            cod_est_prf=existe.get('cod_est_prf', 1)  # Mantener el estado actual
        )

        await self.repository.update(modelo)

        return {
            "success": True,
            "message": "Perfil actualizado correctamente"
        }

    async def cambiar_estado_perfil(self, contract: CambiarEstadoPerfilContract) -> dict:
        """Activa o desactiva un perfil"""
        # Verificar que el perfil existe
        existe = await self.repository.verificar_perfil_existe(contract.cod_prf)

        if not existe:
            return {
                "success": False,
                "message": "El perfil no existe"
            }

        await self.repository.actualizar_estado(contract.cod_prf, contract.cod_est_prf)

        estado_texto = "activado" if contract.cod_est_prf == 1 else "desactivado"
        return {
            "success": True,
            "message": f"Perfil {estado_texto} correctamente"
        }

