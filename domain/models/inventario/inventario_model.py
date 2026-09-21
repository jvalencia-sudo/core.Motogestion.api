from typing import List, Optional

from pydantic import Field

from domain.models.base_model import BaseSchema


class MovimientoItem(BaseSchema):
    """Una línea del kardex de inventario."""
    cod_mov: int
    cod_pro: int
    nombre_pro: Optional[str] = None
    tipo: str                     # ENTRADA / SALIDA / AJUSTE
    cantidad: int
    stock_ant: Optional[int] = None
    stock_nue: Optional[int] = None
    motivo: Optional[str] = None
    documento_usu: Optional[str] = None
    fecha: Optional[str] = None
    referencia: Optional[str] = None


class ProductoStock(BaseSchema):
    """Producto con su stock, para las pantallas de entrada y toma física."""
    cod_pro: int
    nombre: Optional[str] = None
    stock: int
    stock_min: Optional[int] = None


class EntradaContract(BaseSchema):
    cod_pro: int = Field(..., gt=0)
    cantidad: int = Field(..., gt=0)          # unidades que entran
    motivo: Optional[str] = None


class TomaFisicaItem(BaseSchema):
    cod_pro: int
    cantidad_fisica: int = Field(..., ge=0)   # cantidad contada real


class TomaFisicaContract(BaseSchema):
    items: List[TomaFisicaItem]
    motivo: Optional[str] = None
