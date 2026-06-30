from typing import List, Optional

from domain.models.base_model import BaseSchema


class MecanicoItem(BaseSchema):
    documento_usu: str
    nombre: str


class TableroItem(BaseSchema):
    """Una orden de trabajo en el tablero del mecánico."""
    consecutivo_ot: int
    fecha: Optional[str] = None       # fecha_elaboracion_ot (para "días en taller")
    placa: Optional[str] = None
    marca: Optional[str] = None
    cliente: Optional[str] = None
    servicio: Optional[str] = None
    estado: Optional[str] = None
    cod_estado: Optional[int] = None
    mecanico: Optional[str] = None
    documento_mecanico: Optional[str] = None


class TableroResponse(BaseSchema):
    es_gestor: bool          # True si puede ver/seleccionar cualquier mecánico (Admin/Recepcionista)
    mecanicos: List[MecanicoItem]  # lista para el selector (vacía si no es gestor)
    items: List[TableroItem]


class CambiarEstadoContract(BaseSchema):
    cod_estado: int
