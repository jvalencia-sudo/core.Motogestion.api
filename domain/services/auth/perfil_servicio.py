from typing import Dict, List

from starlette.status import HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND

from domain.contracts.auth.perfil_contract import (
    CrearPerfilContract,
    ActualizarPerfilContract,
    CambiarEstadoPerfilContract,
    PerfilDetalleContract
)
from domain.models.auth.perfil_modelo import PerfilModelo
from domain.services.base_service import BaseService
from infrastructure.exceptions.domain_exception import DomainException
from repository.auth.perfil_repositorio import PerfilRepositorio

MAX_PERFILES_POR_TALLER = 10


class PerfilServicio(BaseService[PerfilModelo, PerfilRepositorio]):
    def __init__(self):
        super().__init__(PerfilRepositorio())

    def __parse__(self, record: Dict) -> PerfilModelo:
        normalized = self.__normalize_keys__(record)
        return PerfilModelo.model_validate(normalized)

    async def obtener_vw_perfiles(self) -> List[PerfilDetalleContract]:
        """Obtiene todos los perfiles con información completa desde la vista,
        más cuántos usuarios activos tiene cada uno (tarjetas de rol, F0-13)."""
        registros = await self.repository.obtener_vw_perfiles()
        conteos = await self.repository.contar_usuarios_por_perfil()
        for registro in registros:
            registro["num_usuarios"] = conteos.get(registro.get("COD_PRF"), 0)
        return self.__parse_all_custom__(registros, PerfilDetalleContract)

    async def crear_perfil(self, contract: CrearPerfilContract, usuario: str) -> dict:
        """Crea un nuevo perfil propio del taller (rol personalizado, F0-13
        ext): desde cero o duplicando los permisos de otro perfil existente.
        Siempre no-administrador -- jamás recibe trato de Administrador."""
        total = await self.repository.contar_perfiles_taller()
        if total >= MAX_PERFILES_POR_TALLER:
            raise DomainException(
                f"Ya existe el máximo de {MAX_PERFILES_POR_TALLER} perfiles para este taller. "
                "Elimina uno que no uses antes de crear otro.",
                HTTP_400_BAD_REQUEST,
            )

        duplicado = await self.repository.buscar_por_nombre(contract.nombre_prf)
        if duplicado:
            raise DomainException(
                "Ya existe un perfil con ese nombre en este taller. Elige otro nombre.",
                HTTP_400_BAD_REQUEST,
            )

        if contract.duplicar_de:
            origen = await self.repository.verificar_perfil_existe(contract.duplicar_de)
            if not origen:
                raise DomainException(
                    "El perfil a duplicar no existe. Recarga la página y vuelve a intentar.",
                    HTTP_404_NOT_FOUND,
                )
            cod_prf = await self.repository.duplicar_perfil(
                contract.nombre_prf,
                contract.descripcion_prf,
                origen["COD_PRF"],
                usuario,
            )
        else:
            modelo = PerfilModelo(
                cod_prf=0,  # Se generará automáticamente
                nombre_prf=contract.nombre_prf,
                descripcion_prf=contract.descripcion_prf,
                es_admin=False,
                cod_est_prf=1,
            )
            cod_prf = await self.repository.create(modelo)

        return {
            "success": True,
            "message": "Perfil creado correctamente",
            "cod_prf": cod_prf
        }

    async def actualizar_perfil(self, contract: ActualizarPerfilContract) -> dict:
        """Renombra/edita un perfil existente. es_admin nunca se toca por
        esta vía -- no se puede retargetear hacia/desde Administrador."""
        existe = await self.repository.verificar_perfil_existe(contract.cod_prf)

        if not existe:
            raise DomainException(
                "El perfil no existe. Recarga la página y vuelve a intentar.", HTTP_404_NOT_FOUND
            )

        if existe.get("ES_ADMIN"):
            raise DomainException(
                "El perfil Administrador no se puede renombrar ni editar: siempre tiene "
                "acceso total. Si necesitas otro rol con menos permisos, crea uno nuevo.",
                HTTP_400_BAD_REQUEST,
            )

        duplicado = await self.repository.buscar_por_nombre(
            contract.nombre_prf, excluir_cod_prf=contract.cod_prf
        )
        if duplicado:
            raise DomainException(
                "Ya existe un perfil con ese nombre en este taller. Elige otro nombre.",
                HTTP_400_BAD_REQUEST,
            )

        modelo = PerfilModelo(
            cod_prf=contract.cod_prf,
            nombre_prf=contract.nombre_prf,
            descripcion_prf=contract.descripcion_prf,
            es_admin=bool(existe.get("ES_ADMIN")),
            cod_est_prf=existe.get("COD_EST_PRF", 1),
        )

        await self.repository.update(modelo)

        return {
            "success": True,
            "message": "Perfil actualizado correctamente"
        }

    async def eliminar_perfil(self, cod_prf: int, usuario: str) -> dict:
        """Elimina un perfil propio del taller: nunca el Administrador, y
        nunca si todavía tiene usuarios asignados (hay que reasignarlos antes)."""
        existe = await self.repository.verificar_perfil_existe(cod_prf)
        if not existe:
            raise DomainException(
                "El perfil no existe. Recarga la página y vuelve a intentar.", HTTP_404_NOT_FOUND
            )

        if existe.get("ES_ADMIN"):
            raise DomainException(
                "El perfil Administrador no se puede eliminar: siempre debe quedar al menos "
                "un administrador en el taller.",
                HTTP_400_BAD_REQUEST,
            )

        num_usuarios = await self.repository.contar_usuarios_de_perfil(cod_prf)
        if num_usuarios > 0:
            raise DomainException(
                "Este rol tiene usuarios asignados. Reasigna sus usuarios a otro rol antes de eliminarlo.",
                HTTP_400_BAD_REQUEST,
            )

        await self.repository.eliminar_perfil(cod_prf, usuario)

        return {
            "success": True,
            "message": "Perfil eliminado correctamente"
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

