import secrets
from typing import Dict, List

from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_503_SERVICE_UNAVAILABLE,
)

from config import settings
from domain.contracts.suscripciones.suscripcion_contract import (
    CheckoutResponseContract,
    PlanContract,
)
from infrastructure.exceptions.domain_exception import DomainException
from infrastructure.providers.payments import wompi_provider
from repository.pagos.pago_repositorio import PagoRepositorio
from repository.planes.plan_repositorio import PlanRepositorio
from repository.talleres.taller_repositorio import TallerRepositorio

DIAS_PLAN = 30  # cada pago activa/renueva 30 días


class SuscripcionServicio:
    """Orquesta el ciclo de pago: plan (catálogo) + pago (billing) + taller (activación)
    + proveedor Wompi. Cada repo toca solo su tabla."""

    def __init__(self):
        self.plan_repo = PlanRepositorio()
        self.pago_repo = PagoRepositorio()
        self.taller_repo = TallerRepositorio()

    async def listar_planes(self) -> List[PlanContract]:
        filas = await self.plan_repo.listar()
        return [
            PlanContract(
                cod_plan=f.get("COD_PLAN"),
                nombre_plan=f.get("NOMBRE_PLAN"),
                precio_plan=f.get("PRECIO_PLAN"),
                max_usuarios=f.get("MAX_USUARIOS"),
                max_motos=f.get("MAX_MOTOS"),
                features=f.get("FEATURES") or {},
                orden=f.get("ORDEN") or 0,
            )
            for f in filas
        ]

    async def crear_checkout(self, cod_taller: int, nombre_plan: str) -> Dict:
        cfg = settings.wompi_config
        if not cfg.configurado:
            raise DomainException(
                "Los pagos aún no están configurados. Contacta a soporte.",
                HTTP_503_SERVICE_UNAVAILABLE,
            )
        plan = await self.plan_repo.get_por_nombre(nombre_plan)
        if not plan:
            raise DomainException(f"El plan '{nombre_plan}' no existe.", HTTP_400_BAD_REQUEST)
        monto = plan.get("PRECIO_PLAN") or 0
        if monto <= 0:
            raise DomainException("Ese plan no requiere pago.", HTTP_400_BAD_REQUEST)

        referencia = f"MG-{cod_taller}-{secrets.token_hex(6)}"
        await self.pago_repo.crear_pendiente(cod_taller, nombre_plan, monto, referencia)

        redirect_url = f"{settings.frontend_url}/planes/gracias"
        url = wompi_provider.construir_url_checkout(
            cfg.checkout_url, cfg.public_key, cfg.integrity_secret,
            referencia, monto * 100, redirect_url,   # Wompi usa centavos
        )
        return CheckoutResponseContract(checkout_url=url, referencia=referencia)

    async def procesar_webhook(self, payload: Dict) -> Dict:
        """Verifica la firma del evento de Wompi y, si el pago fue APROBADO, activa
        la suscripción del taller (prueba/vencido -> activo, +30 días)."""
        cfg = settings.wompi_config
        if not wompi_provider.verificar_evento(payload, cfg.events_secret):
            raise DomainException("Firma de webhook inválida", HTTP_401_UNAUTHORIZED)

        tx = wompi_provider.leer_transaccion(payload)
        if not tx:
            return {"ok": True, "ignored": "sin transacción"}
        referencia, estado_tx, txid = tx

        pago = await self.pago_repo.get_por_referencia(referencia)
        if not pago:
            return {"ok": True, "ignored": "referencia desconocida"}
        if pago.get("ESTADO") != "PENDING":
            return {"ok": True, "ignored": "pago ya procesado"}

        if estado_tx == "APPROVED":
            await self.pago_repo.marcar_estado(referencia, "APPROVED", txid)
            await self.taller_repo.activar_suscripcion(
                pago.get("COD_TALLER"), pago.get("NOMBRE_PLAN"), DIAS_PLAN
            )
            return {"ok": True, "estado": "APPROVED"}
        if estado_tx in ("DECLINED", "VOIDED", "ERROR"):
            await self.pago_repo.marcar_estado(referencia, "DECLINED", txid)
            return {"ok": True, "estado": "DECLINED"}
        return {"ok": True, "estado": estado_tx}

    async def listar_pagos(self, cod_taller: int) -> List[Dict]:
        return await self.pago_repo.listar_por_taller(cod_taller)
