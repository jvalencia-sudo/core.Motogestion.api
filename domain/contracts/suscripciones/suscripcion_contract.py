from typing import Dict, Optional

from domain.contracts.base_contract import BaseContractSchema


class CheckoutContract(BaseContractSchema):
    """Solicitud de checkout para un plan."""
    plan: str


class PlanContract(BaseContractSchema):
    """Un plan del catálogo (para la pantalla de precios).

    `precio_plan` es el precio de catálogo (lo que se tacha cuando aplica el
    fundador). `precio_a_pagar` es lo que de verdad pagaría/paga el taller
    (quien llama): su precio ya pactado si lo tiene, si no el fundador
    mientras haya cupos, si no `precio_plan`. El front nunca decide esto por
    su cuenta -- siempre viene calculado del backend."""
    cod_plan: int
    nombre_plan: str
    precio_plan: int
    precio_a_pagar: int
    max_usuarios: Optional[int] = None
    max_motos: Optional[int] = None
    features: Dict = {}
    orden: int = 0


class CheckoutResponseContract(BaseContractSchema):
    """Datos para que el front abra el Widget de Wompi (modal embebido, sin
    salir del sitio) -- en vez de un link de redirect al Web Checkout. Sin
    redirect_url a propósito: el resultado se maneja en el callback del
    widget, no con una navegación de página completa."""
    public_key: str
    currency: str
    amount_in_cents: int
    reference: str
    signature: str


class PagoContract(BaseContractSchema):
    """Un pago del historial del taller (vista de 'Suscripción' en Administración)."""
    cod_pago: int
    nombre_plan: str
    monto: int
    estado: str  # PENDING | APPROVED | DECLINED
    fecha: str   # 'YYYY-MM-DD HH:MM'
