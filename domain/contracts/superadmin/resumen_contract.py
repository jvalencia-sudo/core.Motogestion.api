from datetime import date
from typing import Dict, List, Optional

from domain.contracts.base_contract import BaseContractSchema


class VencimientoProximoContract(BaseContractSchema):
    """Un taller activo cuya suscripción vence en los próximos días (F0-14:
    Resumen). El teléfono se manda para que el front construya el link wa.me --
    el backend no construye URLs de WhatsApp."""
    cod_taller: int
    nombre_tal: str
    telefono_tal: Optional[str] = None
    fecha_fin_susc_tal: Optional[date] = None
    dias_restantes: Optional[int] = None


class ResumenPlataformaContract(BaseContractSchema):
    mrr: int
    talleres_por_estado: Dict[str, int]
    cupos_fundador_restantes: int
    total_talleres: int
    conversion_prueba_pago: float  # 0..1
    vencimientos_proximos: List[VencimientoProximoContract]
