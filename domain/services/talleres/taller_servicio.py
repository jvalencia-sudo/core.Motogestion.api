import random
import time
from typing import Dict, List, Optional

from domain.contracts.talleres.taller_contract import (
    TallerRegistroContract,
    TallerRegistroResponse,
    TallerUpdateContract,
)
from domain.models.talleres.taller_model import TallerModel
from domain.services.base_service import BaseService
from infrastructure.exceptions.domain_exception import DomainException
from infrastructure.utils.tenant_context import set_tenant
from repository.talleres.taller_repositorio import TallerRepositorio


class TallerServicio(BaseService[TallerModel, TallerRepositorio]):
    def __init__(self):
        super().__init__(TallerRepositorio())

    def __parse__(self, record: Dict) -> TallerModel:
        return TallerModel.model_validate(self.__normalize_keys__(record))

    # ---- Gestión (para la futura vista de administración de talleres) ----

    async def listar(self) -> List[TallerModel]:
        return await self.get_all()

    async def obtener(self, cod_taller: int) -> Optional[TallerModel]:
        return await self.get_by_id(cod_taller)

    async def actualizar(self, cod_taller: int, contract: TallerUpdateContract) -> TallerModel:
        taller = await self.obtener(cod_taller)
        if not taller:
            raise DomainException("Taller no encontrado", 404)
        campos = contract.model_dump(exclude_none=True)
        await self.repository.actualizar(cod_taller, campos)
        return await self.obtener(cod_taller)

    # ---- Registro / onboarding ----

    async def registrar(self, contract: TallerRegistroContract) -> TallerRegistroResponse:
        """Registra un taller nuevo: crea el tenant, su usuario dueño (pre-registrado)
        y los catálogos base. El dueño entra luego con su correo (login cerrado)."""
        # 1) Crear el taller (talleres no tiene RLS, no requiere contexto)
        set_tenant(None)
        cod_taller = await self.repository.crear_taller(
            contract.nombre_tal, contract.correo, contract.nit_tal
        )

        # 2) Desde aquí, lo que se inserte cae en el taller nuevo (DEFAULT app.tenant_id)
        set_tenant(cod_taller)
        # Perfiles propios del taller (Admin/Mecánico/Recepcionista) ANTES del dueño,
        # que referencia el perfil Admin de SU taller.
        await self.repository.sembrar_perfiles()
        nombre, apellido = self._partir_nombre(contract.nombre_dueno)
        await self.repository.crear_dueno(
            self._documento_provisional(), nombre, apellido, contract.correo
        )
        await self.repository.sembrar_catalogos()

        return TallerRegistroResponse(
            cod_taller=cod_taller,
            nombre_tal=contract.nombre_tal,
            correo=contract.correo,
        )

    @staticmethod
    def _documento_provisional() -> str:
        return f"{str(int(time.time()))[-8:]}{random.randint(100, 999)}"

    @staticmethod
    def _partir_nombre(nombre_completo: str):
        partes = nombre_completo.strip().split()
        if len(partes) >= 2:
            return partes[0], " ".join(partes[1:])
        return (partes[0] if partes else "Dueño"), "Taller"
