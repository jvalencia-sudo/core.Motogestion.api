from typing import List
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND

from domain.contracts.ordenes_trabajo.pago_orden_contract import (
    PagoOrdenCreateContract,
    PagoOrdenResponseContract,
)
from domain.models.ordenes_trabajo.pago_orden_modelo import PagoOrdenModelo, VwPagosOrdenModelo
from domain.services.base_service import BaseService
from infrastructure.exceptions.domain_exception import DomainException
from repository.ordenes_trabajo.pago_orden_repositorio import PagoOrdenRepositorio
from repository.ordenes_trabajo.orden_trabajo_repositorio import OrdenTrabajoRepositorio

ESTADO_ANULADA = 5


class PagoOrdenServicio(BaseService[PagoOrdenModelo, PagoOrdenRepositorio]):
    def __init__(self):
        super().__init__(PagoOrdenRepositorio())
        self.orden_repository = OrdenTrabajoRepositorio()

    def __parse__(self, record: dict) -> PagoOrdenModelo:
        return PagoOrdenModelo.model_validate(record)

    def _mapear(self, record: dict) -> PagoOrdenResponseContract:
        modelo = self.__parse_custom__(record, VwPagosOrdenModelo)
        return PagoOrdenResponseContract(**modelo.model_dump())

    async def _obtener_orden_o_404(self, consecutivo_ot: int) -> dict:
        orden = await self.orden_repository.obtener_orden_por_id(consecutivo_ot)
        if not orden:
            raise DomainException(
                f"Orden de trabajo con consecutivo {consecutivo_ot} no encontrada",
                HTTP_404_NOT_FOUND,
            )
        return orden

    async def registrar_pago(
        self,
        consecutivo_ot: int,
        contract: PagoOrdenCreateContract,
        documento_usu: str,
    ) -> PagoOrdenResponseContract:
        """F1-07: registra un abono/pago a una orden. No valida contra el
        saldo -- un pago mayor al saldo pendiente no está bloqueado (no es un
        criterio de este ticket)."""
        orden = await self._obtener_orden_o_404(consecutivo_ot)
        if orden.get("COD_OT_EST_OT") == ESTADO_ANULADA:
            raise DomainException(
                "No se puede registrar un pago para una orden anulada",
                HTTP_400_BAD_REQUEST,
            )

        nuevo_pago = PagoOrdenModelo(
            consecutivo_ot_pago=consecutivo_ot,
            valor_pago=contract.valor_pago,
            metodo_pago=contract.metodo_pago,
            documento_usu_pago=documento_usu,
            referencia_pago=contract.referencia_pago,
        )
        cod_pago_orden = await self.repository.create(nuevo_pago)

        return await self.obtener_pago_por_id(cod_pago_orden)

    async def obtener_pago_por_id(self, cod_pago_orden: int) -> PagoOrdenResponseContract:
        registro = await self.repository.obtener_por_id(cod_pago_orden)
        if not registro:
            raise DomainException(
                f"Pago con código {cod_pago_orden} no encontrado", HTTP_404_NOT_FOUND
            )
        return self._mapear(registro)

    async def listar_pagos_por_orden(self, consecutivo_ot: int) -> List[PagoOrdenResponseContract]:
        await self._obtener_orden_o_404(consecutivo_ot)
        registros = await self.repository.listar_por_orden(consecutivo_ot)
        return [self._mapear(r) for r in registros]

    async def anular_pago(
        self, cod_pago_orden: int, motivo: str, documento_usu: str
    ) -> PagoOrdenResponseContract:
        """Los pagos no se editan ni se borran -- esta es la única forma de
        revertir uno, y queda la auditoría de quién/cuándo/por qué."""
        pago = await self.obtener_pago_por_id(cod_pago_orden)
        if pago.anulado_pago:
            raise DomainException("Este pago ya está anulado", HTTP_400_BAD_REQUEST)

        await self.repository.anular(cod_pago_orden, motivo, documento_usu)
        return await self.obtener_pago_por_id(cod_pago_orden)
