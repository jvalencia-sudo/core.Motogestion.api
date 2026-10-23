from typing import List, Optional

from pydantic import Field, field_validator

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
    # F1-07: si la orden queda a Entregada (4) con saldo pendiente, el
    # backend lo rechaza salvo que el front confirme "entregar a crédito".
    confirmar_credito: bool = False


class AgregarNotaContract(BaseSchema):
    """F1-08: nota del mecánico (ej. "Necesito repuesto") -- se AGREGA a la
    observación interna, nunca la reemplaza (ahí también vive el trabajo
    pedido con el que se abrió la orden)."""
    nota: str = Field(..., min_length=3, max_length=300)

    @field_validator("nota")
    @classmethod
    def no_solo_espacios(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("La nota no puede estar vacía")
        return v.strip()


class NotaTableroResponse(BaseSchema):
    consecutivo_ot: int
    observacion_ot: Optional[str] = None
