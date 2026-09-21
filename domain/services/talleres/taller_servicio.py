import random
import time
from datetime import date, timedelta
from typing import Dict, List, Optional

from starlette.status import HTTP_400_BAD_REQUEST

from domain.contracts.talleres.taller_contract import (
    TallerConfigManoObraContract,
    TallerRegistroContract,
    TallerRegistroResponse,
    TallerSuscripcionContract,
    TallerUpdateContract,
)
from domain.models.talleres.taller_model import TallerModel
from domain.services.base_service import BaseService
from infrastructure.exceptions.domain_exception import DomainException
from infrastructure.utils.tenant_context import set_tenant
from repository.talleres.taller_repositorio import TallerRepositorio
from repository.auth.perfil_repositorio import PerfilRepositorio
from repository.admin.admin_user_repository import AdminUserRepository
from repository.marcas.marca_repositorio import MarcaRepositorio
from repository.productos.impuesto_repositorio import ImpuestoRepositorio

# Catálogos base con que arranca un taller nuevo (política de onboarding).
MARCAS_INICIALES = ["Yamaha", "Honda", "Suzuki", "Kawasaki", "Bajaj", "AKT", "KTM", "Auteco"]
IMPUESTOS_INICIALES = [("IVA", 19.00), ("IVA Reducido", 5.00), ("Excluido", 0.00)]

# Política de prueba gratis (días). Anti-abuso: 1 correo = 1 taller (índice único).
DIAS_PRUEBA = 30


class TallerServicio(BaseService[TallerModel, TallerRepositorio]):
    def __init__(self):
        super().__init__(TallerRepositorio())
        # Repos dueños de cada tabla que interviene en el onboarding (orquestación).
        self.perfil_repo = PerfilRepositorio()
        self.usuario_repo = AdminUserRepository()
        self.marca_repo = MarcaRepositorio()
        self.impuesto_repo = ImpuestoRepositorio()

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

    # ---- Config de mano de obra (para el dueño/Admin de su propio taller) ----

    async def obtener_config_mano_obra(self, cod_taller: int) -> TallerConfigManoObraContract:
        taller = await self.obtener(cod_taller)
        if not taller:
            raise DomainException("Taller no encontrado", 404)
        return TallerConfigManoObraContract(
            modo_mano_obra=taller.modo_mano_obra or "HORAS",
            tarifa_hora_pred=taller.tarifa_hora_pred or 0,
        )

    async def actualizar_config_mano_obra(
        self, cod_taller: int, contract: TallerConfigManoObraContract
    ) -> TallerConfigManoObraContract:
        taller = await self.obtener(cod_taller)
        if not taller:
            raise DomainException("Taller no encontrado", 404)
        await self.repository.actualizar(cod_taller, contract.model_dump())
        return await self.obtener_config_mano_obra(cod_taller)

    # ---- Suscripción (estado del plan/trial para el front) ----

    async def obtener_suscripcion(self, cod_taller: int) -> TallerSuscripcionContract:
        susc = await self.repository.get_suscripcion(cod_taller)
        if not susc:
            raise DomainException("Taller no encontrado", 404)
        estado = susc.get("ESTADO_TAL")
        fecha_fin = susc.get("FECHA_FIN_SUSC_TAL")
        dias = (fecha_fin - date.today()).days if fecha_fin else None
        vencido = estado == "prueba" and fecha_fin is not None and fecha_fin < date.today()
        return TallerSuscripcionContract(
            estado=estado,
            plan=susc.get("PLAN_TAL"),
            fecha_fin=str(fecha_fin) if fecha_fin else None,
            dias_restantes=dias,
            vencido=vencido,
        )

    # ---- Registro / onboarding ----

    async def registrar(self, contract: TallerRegistroContract) -> TallerRegistroResponse:
        """Registra un taller nuevo: crea el tenant, su usuario dueño (pre-registrado)
        y los catálogos base. El dueño entra luego con su correo (login cerrado)."""
        # 0) Anti-abuso: un correo = un taller (evita renovar el trial con otra cuenta).
        set_tenant(None)
        if await self.repository.existe_por_correo(contract.correo):
            raise DomainException(
                "Ya existe un taller registrado con ese correo.",
                HTTP_400_BAD_REQUEST,
            )

        # 1) Crear el taller con su ventana de prueba (fecha_fin_susc = hoy + DIAS_PRUEBA).
        fecha_fin = date.today() + timedelta(days=DIAS_PRUEBA)
        cod_taller = await self.repository.crear_taller(
            contract.nombre_tal, contract.correo, contract.nit_tal, fecha_fin
        )

        # 2) Desde aquí, lo que se inserte cae en el taller nuevo (DEFAULT app.tenant_id).
        set_tenant(cod_taller)
        # Perfiles propios del taller (Admin/Mecánico/Recepcionista) ANTES del dueño,
        # que referencia el perfil Admin de SU taller.
        await self.perfil_repo.sembrar_taller()
        cod_prf_admin = await self.perfil_repo.obtener_cod_admin()
        nombre, apellido = self._partir_nombre(contract.nombre_dueno)
        await self.usuario_repo.crear_pre_registrado(
            self._documento_provisional(), nombre, apellido, None, contract.correo,
            cod_prf_admin, 1, cod_est=1, cod_tipo=1,
        )
        # Catálogos base del taller.
        for nombre_mar in MARCAS_INICIALES:
            await self.marca_repo.crear(nombre_mar)
        for nombre_imp, pct in IMPUESTOS_INICIALES:
            await self.impuesto_repo.crear(nombre_imp, pct)

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
