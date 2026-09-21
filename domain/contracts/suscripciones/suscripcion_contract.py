from typing import Dict, Optional

from domain.contracts.base_contract import BaseContractSchema


class CheckoutContract(BaseContractSchema):
    """Solicitud de checkout para un plan."""
    plan: str


class PlanContract(BaseContractSchema):
    """Un plan del catálogo (para la pantalla de precios)."""
    cod_plan: int
    nombre_plan: str
    precio_plan: int
    max_usuarios: Optional[int] = None
    max_motos: Optional[int] = None
    features: Dict = {}
    orden: int = 0


class CheckoutResponseContract(BaseContractSchema):
    """Respuesta del checkout: link de pago de Wompi + referencia."""
    checkout_url: str
    referencia: str
