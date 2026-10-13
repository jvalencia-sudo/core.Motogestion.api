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
    """Respuesta del checkout: link de pago de Wompi + referencia."""
    checkout_url: str
    referencia: str
