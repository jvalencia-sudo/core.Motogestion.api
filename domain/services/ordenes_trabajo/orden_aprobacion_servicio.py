from typing import List, Optional

from starlette.status import HTTP_404_NOT_FOUND, HTTP_409_CONFLICT

from domain.contracts.ordenes_trabajo.orden_trabajo_contract import (
    AprobarCotizacionResponseContract,
)
from domain.services.ordenes_trabajo.orden_trabajo_servicio import OrdenTrabajoServicio
from infrastructure.exceptions.domain_exception import DomainException
from infrastructure.utils.tenant_context import reset_tenant, set_tenant
from repository.ordenes_trabajo.orden_aprobacion_repositorio import OrdenAprobacionRepositorio
from repository.ordenes_trabajo.orden_trabajo_publica_repositorio import (
    OrdenTrabajoPublicaRepositorio,
)
from repository.talleres.taller_repositorio import TallerRepositorio


class OrdenAprobacionServicio:
    """F2-03: aprobación de cotización desde el link público (sin sesión),
    opcional por taller. Diseño: NO es un estado nuevo de cod_ot_est_ot (esa
    columna es libre, sin tabla de transiciones, y tocarla arrastraría
    tablero/kanban/reportes/PDF que ya asumen 1-6) -- es una capa ortogonal
    sobre la orden, igual mecanismo de resolución de token que
    OrdenTrabajoPublicaServicio."""

    def __init__(self):
        self.publica_repo = OrdenTrabajoPublicaRepositorio()
        self.orden_servicio = OrdenTrabajoServicio()
        self.aprobacion_repo = OrdenAprobacionRepositorio()
        self.taller_repo = TallerRepositorio()

    async def aprobar(
        self, token: str, ip: Optional[str], user_agent: Optional[str]
    ) -> AprobarCotizacionResponseContract:
        resuelto = await self.publica_repo.resolver_token(token)
        if not resuelto:
            raise DomainException("Orden no encontrada", HTTP_404_NOT_FOUND)

        cod_taller = resuelto["COD_TALLER"]
        consecutivo_ot = resuelto["CONSECUTIVO_OT"]

        token_guard = set_tenant(cod_taller)
        try:
            config = await self.taller_repo.obtener_config_marca(cod_taller) or {}
            if not config.get("EXIGE_APROBACION_COTIZACION_TAL"):
                raise DomainException(
                    "Esta orden no requiere aprobación de cotización", HTTP_409_CONFLICT
                )

            orden = await self.orden_servicio.obtener_orden_por_id(consecutivo_ot)
            if orden.cod_ot_est_ot != 2:
                raise DomainException(
                    "La orden no está en un estado que permita aprobar la cotización",
                    HTTP_409_CONFLICT,
                )
            if not orden.total_ot or orden.total_ot <= 0:
                raise DomainException(
                    "La orden no tiene cotización para aprobar", HTTP_409_CONFLICT
                )

            # Idempotente: si ya hay una aprobación vigente, por invariante su
            # instantánea coincide con la cotización actual (cualquier cambio
            # a los ítems invalida la vigente -- ver
            # OrdenTrabajoServicio.agregar_producto/retirar_producto). Se
            # devuelve tal cual, sin insertar una fila nueva.
            vigente = await self.aprobacion_repo.obtener_vigente(consecutivo_ot)
            if vigente:
                return AprobarCotizacionResponseContract(
                    aprobado_en=vigente["APROBADO_EN"],
                    total_snapshot=float(vigente["TOTAL_SNAPSHOT"]),
                )

            creada = await self.aprobacion_repo.crear_aprobacion(
                consecutivo_ot, ip, user_agent, self._items_snapshot(orden), orden.total_ot
            )
            return AprobarCotizacionResponseContract(
                aprobado_en=creada["APROBADO_EN"],
                total_snapshot=float(creada["TOTAL_SNAPSHOT"]),
            )
        finally:
            reset_tenant(token_guard)

    @staticmethod
    def _items_snapshot(orden) -> List[dict]:
        """Instantánea legal de la cotización aprobada -- solo ítems activos
        y cobrados (lo que realmente compone el total aprobado)."""
        return [
            {
                "cod_pro": det.cod_pro_deto,
                "nombre": det.nombre_pro,
                "cantidad": float(det.cantidad_deto),
                "valor_unitario": det.valor_unitario_deto,
                "subtotal": det.subtotal,
            }
            for det in (orden.detalles or [])
            if not det.retirado and det.cobrar_deto
        ]
