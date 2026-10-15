import logging
import secrets
from typing import Dict, List, Optional

from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_503_SERVICE_UNAVAILABLE,
)

from config import settings
from domain.contracts.suscripciones.suscripcion_contract import (
    CheckoutResponseContract,
    PagoContract,
    PlanContract,
)
from infrastructure.exceptions.domain_exception import DomainException
from infrastructure.providers.payments import wompi_provider
from repository.pagos.pago_repositorio import PagoRepositorio
from repository.planes.plan_repositorio import PlanRepositorio
from repository.talleres.taller_repositorio import TallerRepositorio

logger = logging.getLogger(__name__)

DIAS_PLAN = 30  # cada pago activa/renueva 30 días

# Precio fundador (F0-08): congelado para los primeros CUPOS_FUNDADOR talleres
# que paguen, mientras mantengan la suscripción. Después, precio_plan vigente.
CUPOS_FUNDADOR = 10
PRECIO_FUNDADOR = 49000


class SuscripcionServicio:
    """Orquesta el ciclo de pago: plan (catálogo) + pago (billing) + taller (activación)
    + proveedor Wompi. Cada repo toca solo su tabla."""

    def __init__(self):
        self.plan_repo = PlanRepositorio()
        self.pago_repo = PagoRepositorio()
        self.taller_repo = TallerRepositorio()

    async def listar_planes(self, cod_taller: Optional[int] = None) -> List[PlanContract]:
        """Catálogo de planes activos. Si se conoce el taller que pregunta
        (sesión iniciada), `precio_a_pagar` es SU precio; si no (landing
        pública), es lo que pagaría un taller nuevo hoy."""
        filas = await self.plan_repo.listar()
        planes = []
        for f in filas:
            precio_plan = f.get("PRECIO_PLAN") or 0
            precio_a_pagar = await self._calcular_monto_a_pagar(cod_taller, precio_plan)
            planes.append(PlanContract(
                cod_plan=f.get("COD_PLAN"),
                nombre_plan=f.get("NOMBRE_PLAN"),
                precio_plan=precio_plan,
                precio_a_pagar=precio_a_pagar,
                max_usuarios=f.get("MAX_USUARIOS"),
                max_motos=f.get("MAX_MOTOS"),
                features=f.get("FEATURES") or {},
                orden=f.get("ORDEN") or 0,
            ))
        return planes

    async def _calcular_monto_a_pagar(self, cod_taller: Optional[int], precio_plan: int) -> int:
        """Precio que paga/pagaría un taller por un plan de pago:
        1. El ya pactado con ese taller (precio_susc_tal), si lo tiene -- congelado,
           no cambia aunque precio_plan o el cupo fundador cambien después.
        2. Si no, precio fundador mientras haya menos de CUPOS_FUNDADOR talleres
           pagando ese precio.
        3. Si no, precio_plan vigente.
        Los planes gratis (precio_plan <= 0, ej. Prueba) no entran en esta cuenta."""
        if precio_plan <= 0:
            return precio_plan
        if cod_taller is not None:
            taller = await self.taller_repo.get_suscripcion(cod_taller)
            precio_pactado = taller.get("PRECIO_SUSC_TAL") if taller else None
            if precio_pactado is not None:
                return precio_pactado
        fundadores = await self.taller_repo.contar_por_precio_susc(PRECIO_FUNDADOR)
        if fundadores < CUPOS_FUNDADOR:
            return PRECIO_FUNDADOR
        return precio_plan

    async def crear_checkout(self, cod_taller: int, nombre_plan: str) -> Dict:
        cfg = settings.wompi_config
        if not cfg.configurado:
            raise DomainException(
                "Los pagos aún no están configurados. Contacta a soporte.",
                HTTP_503_SERVICE_UNAVAILABLE,
            )
        plan = await self.plan_repo.get_por_nombre(nombre_plan)
        if not plan or not plan.get("ACTIVO"):
            raise DomainException(f"El plan '{nombre_plan}' no existe.", HTTP_400_BAD_REQUEST)
        monto = await self._calcular_monto_a_pagar(cod_taller, plan.get("PRECIO_PLAN") or 0)
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
        referencia, estado_tx, txid, monto_centavos = tx

        pago = await self.pago_repo.get_por_referencia(referencia)
        if not pago:
            return {"ok": True, "ignored": "referencia desconocida"}
        if pago.get("ESTADO") != "PENDING":
            return {"ok": True, "ignored": "pago ya procesado"}

        if estado_tx == "APPROVED":
            monto_esperado = pago.get("MONTO") or 0
            if monto_centavos != monto_esperado * 100:
                # No se activa nada: puede ser un bug propio (precio recalculado
                # distinto entre checkout y webhook) o un evento manipulado. La
                # firma ya se verificó arriba, pero igual no confiamos en el monto
                # sin chequearlo contra lo que de verdad se esperaba cobrar.
                await self.pago_repo.marcar_estado(referencia, "DECLINED", txid)
                logger.error(
                    "Webhook Wompi con monto distinto al esperado: referencia=%s "
                    "esperado_centavos=%s recibido_centavos=%s",
                    referencia, monto_esperado * 100, monto_centavos,
                )
                return {"ok": True, "estado": "MONTO_INVALIDO"}

            await self.pago_repo.marcar_estado(referencia, "APPROVED", txid)
            cod_taller = pago.get("COD_TALLER")
            taller = await self.taller_repo.get_suscripcion(cod_taller)
            if taller and taller.get("PRECIO_SUSC_TAL") is None:
                # Se congela la primera vez que paga: cambios futuros de precio_plan
                # o del cupo fundador no le afectan mientras mantenga la suscripción.
                await self.taller_repo.actualizar(cod_taller, {"precio_susc_tal": monto_esperado})
            await self.taller_repo.activar_suscripcion(
                cod_taller, pago.get("NOMBRE_PLAN"), DIAS_PLAN
            )
            return {"ok": True, "estado": "APPROVED"}
        if estado_tx in ("DECLINED", "VOIDED", "ERROR"):
            await self.pago_repo.marcar_estado(referencia, "DECLINED", txid)
            return {"ok": True, "estado": "DECLINED"}
        return {"ok": True, "estado": estado_tx}

    async def listar_pagos(self, cod_taller: int) -> List[PagoContract]:
        pagos = await self.pago_repo.listar_por_taller(cod_taller)
        return [
            PagoContract(
                cod_pago=p.get("COD_PAGO"),
                nombre_plan=p.get("NOMBRE_PLAN"),
                monto=p.get("MONTO"),
                estado=p.get("ESTADO"),
                fecha=p.get("FECHA"),
            )
            for p in pagos
        ]
