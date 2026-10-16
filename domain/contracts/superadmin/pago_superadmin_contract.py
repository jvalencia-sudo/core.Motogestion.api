from typing import List, Optional

from domain.contracts.base_contract import BaseContractSchema


class PagoPlataformaContract(BaseContractSchema):
    cod_pago: int
    cod_taller: int
    nombre_tal: str
    nombre_plan: str
    monto: int
    estado: str
    medio: str
    detalle_medio: Optional[str] = None
    fecha: str


class AlertaPagoContract(BaseContractSchema):
    cod_pago: int
    cod_taller: int
    nombre_tal: str
    monto: int
    fecha: str


class AlertasPagoContract(BaseContractSchema):
    aprobados_sin_suscripcion_activa: List[AlertaPagoContract]
    pendientes_viejos: List[AlertaPagoContract]
