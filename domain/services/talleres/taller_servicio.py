import random
import time
from datetime import timedelta
from typing import Dict, List, Optional

from starlette.status import HTTP_400_BAD_REQUEST


from domain.contracts.talleres.taller_contract import (
    TallerConfigContract,
    TallerConfigResponse,
    TallerRegistroContract,
    TallerRegistroResponse,
    TallerSuscripcionContract,
    TallerUpdateContract,
    VistaPreviaOrdenContract,
)
from domain.models.talleres.taller_model import TallerModel
from domain.services.base_service import BaseService
from infrastructure.exceptions.domain_exception import DomainException
from infrastructure.utils.fecha_bogota import hoy_bogota
from infrastructure.utils.imagen import LOGO_MAX_BYTES, TIPOS_LOGO_PERMITIDOS, redimensionar_logo
from infrastructure.utils.marca_taller import ConfigMarcaTaller
from infrastructure.utils.tenant_context import set_tenant
from repository.talleres.taller_repositorio import TallerRepositorio
from repository.talleres.taller_logo_repositorio import TallerLogoRepositorio
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
        self.logo_repo = TallerLogoRepositorio()

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

    # ---- Config del propio taller ("Mi taller": mano de obra + comprobante) ----

    async def obtener_config(self, cod_taller: int) -> TallerConfigResponse:
        taller = await self.obtener(cod_taller)
        if not taller:
            raise DomainException(
                "Tu taller no existe o fue eliminado. Escríbenos a soporte.", 404
            )
        return TallerConfigResponse(
            modo_mano_obra=taller.modo_mano_obra or "HORAS",
            tarifa_hora_pred=taller.tarifa_hora_pred or 0,
            telefono_tal=taller.telefono_tal,
            direccion_tal=taller.direccion_tal,
            texto_pie_comprobante=taller.texto_pie_comprobante,
            nombre_comercial_tal=taller.nombre_comercial_tal,
            whatsapp_tal=taller.whatsapp_tal,
            color_principal_tal=taller.color_principal_tal or "#00B06E",
            texto_condiciones_tal=taller.texto_condiciones_tal,
            texto_pie_tal=taller.texto_pie_tal,
            mostrar_precios_unitarios_tal=(
                taller.mostrar_precios_unitarios_tal
                if taller.mostrar_precios_unitarios_tal is not None else True
            ),
            mostrar_mecanico_tal=(
                taller.mostrar_mecanico_tal if taller.mostrar_mecanico_tal is not None else True
            ),
            mostrar_firma_cliente_tal=bool(taller.mostrar_firma_cliente_tal),
            nombre_tal=taller.nombre_tal,
            nit_tal=taller.nit_tal,
            correo_tal=taller.correo_tal,
            tiene_logo=await self.logo_repo.existe(cod_taller),
        )

    async def actualizar_config(
        self, cod_taller: int, contract: TallerConfigContract
    ) -> TallerConfigResponse:
        taller = await self.obtener(cod_taller)
        if not taller:
            raise DomainException(
                "Tu taller no existe o fue eliminado. Escríbenos a soporte.", 404
            )
        await self.repository.actualizar(cod_taller, contract.model_dump())
        return await self.obtener_config(cod_taller)

    # ---- Logo del taller (F1-09) ----

    async def subir_logo(self, cod_taller: int, contenido: bytes, content_type: str) -> None:
        if content_type not in TIPOS_LOGO_PERMITIDOS:
            raise DomainException(
                "Formato no soportado. Usa PNG, JPG o WebP.", HTTP_400_BAD_REQUEST
            )
        if len(contenido) > LOGO_MAX_BYTES:
            raise DomainException(
                "El archivo supera el máximo de 2MB.", HTTP_400_BAD_REQUEST
            )
        try:
            logo_png = redimensionar_logo(contenido)
        except ValueError as exc:
            raise DomainException(str(exc), HTTP_400_BAD_REQUEST) from exc
        await self.logo_repo.guardar(cod_taller, logo_png, "image/png")

    async def obtener_logo(self, cod_taller: int) -> Optional[Dict]:
        return await self.logo_repo.obtener(cod_taller)

    # ---- Personalización de la orden / vista previa (F1-09) ----

    async def config_marca(self, cod_taller: int) -> ConfigMarcaTaller:
        """Config de personalización (ya guardada) + logo, lista para pasarle
        a los generadores de PDF."""
        config = await self.repository.obtener_config_marca(cod_taller) or {}
        logo = await self.logo_repo.obtener(cod_taller)
        return ConfigMarcaTaller(
            nombre_comercial=config.get("NOMBRE_COMERCIAL_TAL"),
            logo_bytes=logo.get("LOGO") if logo else None,
            color_principal=config.get("COLOR_PRINCIPAL_TAL") or "#00B06E",
            texto_condiciones=config.get("TEXTO_CONDICIONES_TAL"),
            texto_pie=config.get("TEXTO_PIE_TAL"),
            mostrar_precios_unitarios=bool(config.get("MOSTRAR_PRECIOS_UNITARIOS_TAL", True)),
            mostrar_mecanico=bool(config.get("MOSTRAR_MECANICO_TAL", True)),
            mostrar_firma_cliente=bool(config.get("MOSTRAR_FIRMA_CLIENTE_TAL", False)),
        )

    async def vista_previa_pdf(
        self, cod_taller: int, contract: VistaPreviaOrdenContract
    ) -> bytes:
        """Genera el PDF de una orden de EJEMPLO con la configuración del
        formulario, SIN guardar nada -- ni en `talleres` ni en una orden
        real. El logo que se usa es el ya guardado (el logo se sube aparte,
        de inmediato)."""
        from infrastructure.utils.pdf_generator import OrdenTrabajoPDFGenerator
        from infrastructure.utils.orden_ejemplo import orden_de_ejemplo

        logo = await self.logo_repo.obtener(cod_taller)
        marca = ConfigMarcaTaller(
            nombre_comercial=contract.nombre_comercial_tal,
            logo_bytes=logo.get("LOGO") if logo else None,
            color_principal=contract.color_principal_tal,
            texto_condiciones=contract.texto_condiciones_tal,
            texto_pie=contract.texto_pie_tal,
            mostrar_precios_unitarios=contract.mostrar_precios_unitarios_tal,
            mostrar_mecanico=contract.mostrar_mecanico_tal,
            mostrar_firma_cliente=contract.mostrar_firma_cliente_tal,
        )
        return OrdenTrabajoPDFGenerator(marca).generar_pdf(orden_de_ejemplo())

    # ---- Suscripción (estado del plan/trial para el front) ----

    async def obtener_suscripcion(self, cod_taller: int) -> TallerSuscripcionContract:
        susc = await self.repository.get_suscripcion(cod_taller)
        if not susc:
            raise DomainException("Taller no encontrado", 404)
        estado = susc.get("ESTADO_TAL")
        fecha_fin = susc.get("FECHA_FIN_SUSC_TAL")
        fecha_creacion = susc.get("FECHA_CREACION_TAL")
        dias = (fecha_fin - hoy_bogota()).days if fecha_fin else None
        vencido = estado == "prueba" and fecha_fin is not None and fecha_fin < hoy_bogota()
        return TallerSuscripcionContract(
            estado=estado,
            plan=susc.get("PLAN_TAL"),
            precio=susc.get("PRECIO_SUSC_TAL"),
            fecha_fin=str(fecha_fin) if fecha_fin else None,
            dias_restantes=dias,
            vencido=vencido,
            miembro_desde=str(fecha_creacion)[:10] if fecha_creacion else None,
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
        fecha_fin = hoy_bogota() + timedelta(days=DIAS_PRUEBA)
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
            cod_prf_admin, True, cod_est=1, cod_tipo=1,
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
