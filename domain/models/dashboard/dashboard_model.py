from typing import List

from domain.models.base_model import BaseSchema


class OrdenPorEstado(BaseSchema):
    cod_ot_est: int
    nombre_ot_est: str
    cantidad: int


class ResumenDashboard(BaseSchema):
    """Resumen agregado del taller para la home. Todo viene acotado por RLS al taller actual."""
    total_clientes: int
    total_motos: int
    total_productos: int
    total_ordenes: int
    ot_activas: int
    productos_bajo_stock: int
    total_reclamos: int
    ordenes_por_estado: List[OrdenPorEstado]
