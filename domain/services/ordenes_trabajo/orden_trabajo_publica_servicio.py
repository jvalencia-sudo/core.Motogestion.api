import base64
from typing import List, Optional

from starlette.status import HTTP_404_NOT_FOUND

from domain.contracts.ordenes_trabajo.orden_trabajo_contract import (
    OrdenPublicaItemContract,
    OrdenPublicaResponseContract,
    OrdenPublicaTallerContract,
    PasoHistorialContract,
)
from domain.services.ordenes_trabajo.orden_trabajo_servicio import OrdenTrabajoServicio
from infrastructure.exceptions.domain_exception import DomainException
from infrastructure.utils.tenant_context import reset_tenant, set_tenant
from repository.ordenes_trabajo.orden_aprobacion_repositorio import OrdenAprobacionRepositorio
from repository.ordenes_trabajo.orden_trabajo_publica_repositorio import (
    OrdenTrabajoPublicaRepositorio,
)
from repository.planes.plan_repositorio import PlanRepositorio
from repository.talleres.taller_logo_repositorio import TallerLogoRepositorio
from repository.talleres.taller_repositorio import TallerRepositorio


class OrdenTrabajoPublicaServicio:
    """F2-01: arma la respuesta del link público de estado (sin login) a
    partir de un token. NUNCA expone el contrato interno de la orden
    (OrdenTrabajoResponseContract) -- ese trae documento/correo/dirección
    del cliente."""

    def __init__(self):
        self.repository = OrdenTrabajoPublicaRepositorio()
        self.orden_servicio = OrdenTrabajoServicio()
        self.taller_repo = TallerRepositorio()
        self.plan_repo = PlanRepositorio()
        self.logo_repo = TallerLogoRepositorio()
        self.aprobacion_repo = OrdenAprobacionRepositorio()

    async def obtener_por_token(self, token: str) -> OrdenPublicaResponseContract:
        resuelto = await self.repository.resolver_token(token)
        if not resuelto:
            raise DomainException("Orden no encontrada", HTTP_404_NOT_FOUND)

        cod_taller = resuelto["COD_TALLER"]
        consecutivo_ot = resuelto["CONSECUTIVO_OT"]

        # A partir de aquí, el resto de repos normales (motos, clientes,
        # detalles) quedan correctamente aislados al taller del token, sin
        # ningún bypass adicional -- mismo mecanismo que ya usa el
        # super-admin al recorrer varios talleres dentro de una petición.
        token_guard = set_tenant(cod_taller)
        try:
            orden = await self.orden_servicio.obtener_orden_por_id(consecutivo_ot)
            config = await self.taller_repo.obtener_config_marca(cod_taller) or {}
            susc = await self.taller_repo.get_suscripcion(cod_taller) or {}
            features = await self.plan_repo.features_de(susc.get("PLAN_TAL"))

            mostrar_detalle = bool(config.get("MOSTRAR_DETALLE_PUBLICO_TAL", True))
            items = self._items_publicos(orden) if mostrar_detalle else None
            total = orden.total_ot if mostrar_detalle else None

            logo = await self.logo_repo.obtener(cod_taller)

            # Entregada(4) y Garantía(6) comparten el mismo tratamiento visual
            # que "entregada" (ver _ESTADO_CLAVE en orden_trabajo_html_pdf.py,
            # mismo criterio ya usado para el PDF).
            es_entregada = orden.cod_ot_est_ot in (4, 6)
            mostrar_mecanico = bool(config.get("MOSTRAR_MECANICO_TAL", True))

            # F2-03: gate de aprobación, opcional por taller -- ver
            # OrdenAprobacionServicio para el diseño completo. Ortogonal al
            # estado interno: la orden sigue en 2 (En Proceso) con o sin esto.
            exige_aprobacion = bool(config.get("EXIGE_APROBACION_COTIZACION_TAL"))
            vigente = (
                await self.aprobacion_repo.obtener_vigente(consecutivo_ot)
                if exige_aprobacion else None
            )
            esperando_aprobacion = (
                exige_aprobacion
                and orden.cod_ot_est_ot == 2
                and bool(total)
                and not vigente
            )

            historial_dict = await self.orden_servicio.repository.obtener_historial_estados(consecutivo_ot)

            return OrdenPublicaResponseContract(
                consecutivo_ot=orden.consecutivo_ot,
                placa_mot=orden.placa_mot,
                ciudad_placa_mot=orden.ciudad_placa_mot,
                marca_moto=orden.marca_moto,
                modelo_mot=orden.modelo_mot,
                kilometraje_ingreso_ot=orden.kilometraje_ingreso_ot,
                mecanico=orden.mecanico if (mostrar_mecanico and orden.mecanico) else None,
                estado_ot=orden.estado_ot,
                cod_ot_est_ot=orden.cod_ot_est_ot,
                fecha_elaboracion_ot=orden.fecha_elaboracion_ot,
                fecha_entrega_ot=orden.fecha_entrega_ot if es_entregada else None,
                items=items,
                total_ot=total,
                taller=OrdenPublicaTallerContract(
                    nombre_comercial=config.get("NOMBRE_COMERCIAL_TAL") or "",
                    whatsapp=config.get("WHATSAPP_TAL"),
                    telefono=config.get("TELEFONO_TAL"),
                    direccion=config.get("DIRECCION_TAL"),
                    color_principal=config.get("COLOR_PRINCIPAL_TAL") or "#00B06E",
                    logo_data_uri=self._logo_data_uri(logo),
                    mostrar_pie_motogestion=not bool(features.get("sin_marca_motogestion")),
                    nit=config.get("NIT_TAL"),
                    horario=config.get("HORARIO_ATENCION_TAL"),
                ),
                diagnostico=orden.diagnostico_ot or None,
                esperando_aprobacion=esperando_aprobacion,
                aprobado_en=vigente["APROBADO_EN"] if vigente else None,
                pasos_historial=[
                    PasoHistorialContract(cod_ot_est_ot=h["COD_OT_EST_OT"], ocurrido_en=h["OCURRIDO_EN"])
                    for h in historial_dict
                ],
            )
        finally:
            reset_tenant(token_guard)

    @staticmethod
    def _items_publicos(orden) -> List[OrdenPublicaItemContract]:
        return [
            OrdenPublicaItemContract(
                nombre=det.nombre_pro,
                tipo=det.tipo_pro,
                cantidad=det.cantidad_deto,
                valor_unitario=det.valor_unitario_deto,
                cobrado=det.cobrar_deto,
                subtotal=det.subtotal if det.cobrar_deto else 0.0,
                detalle=det.descripcion_pro,
                retirado=det.retirado,
                motivo_retiro=det.motivo_retiro,
            )
            for det in (orden.detalles or [])
        ]

    @staticmethod
    def _logo_data_uri(logo: Optional[dict]) -> Optional[str]:
        if not logo or not logo.get("LOGO"):
            return None
        contenido = base64.b64encode(logo["LOGO"]).decode("ascii")
        tipo = logo.get("CONTENT_TYPE") or "image/png"
        return f"data:{tipo};base64,{contenido}"
