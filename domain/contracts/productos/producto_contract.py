from typing import Optional, List
from pydantic import Field

from domain.contracts.base_contract import BaseContractSchema


class ImpuestoProductoContract(BaseContractSchema):
    """Contrato para asignar un impuesto a un producto"""
    cod_imp: int = Field(..., description="Código del impuesto")
    porcentaje: float = Field(..., description="Porcentaje del impuesto a aplicar", ge=0, le=100)


class ImpuestoResponseContract(BaseContractSchema):
    """Contrato de respuesta para un impuesto asociado a un producto"""
    cod_imp: int
    nombre_imp: str
    porcentaje: float


class ProductoCreateContract(BaseContractSchema):
    """Contrato para crear un producto con sus impuestos"""
    nombre_pro: str = Field(..., min_length=1, max_length=70, description="Nombre del producto")
    descripcion_pro: str = Field(..., min_length=1, max_length=500, description="Descripción del producto")
    stock_pro: int = Field(..., gt=0, description="Stock actual del producto (debe ser mayor a 0)")
    stock_pro_min: int = Field(..., gt=0, description="Stock mínimo del producto (debe ser mayor a 0)")
    precio_pro: int = Field(..., gt=0, description="Precio del producto (debe ser mayor a 0)")
    impuestos: Optional[List[ImpuestoProductoContract]] = Field(default=[], description="Lista de impuestos a aplicar")


class ProductoUpdateContract(BaseContractSchema):
    """Contrato para actualizar un producto"""
    nombre_pro: Optional[str] = Field(None, min_length=1, max_length=70, description="Nombre del producto")
    descripcion_pro: Optional[str] = Field(None, min_length=1, max_length=500, description="Descripción del producto")
    stock_pro: Optional[int] = Field(None, gt=0, description="Stock actual del producto (debe ser mayor a 0)")
    stock_pro_min: Optional[int] = Field(None, gt=0, description="Stock mínimo del producto (debe ser mayor a 0)")
    precio_pro: Optional[int] = Field(None, gt=0, description="Precio del producto (debe ser mayor a 0)")
    impuestos: Optional[List[ImpuestoProductoContract]] = Field(None, description="Lista de impuestos a aplicar")


class ProductoResponseContract(BaseContractSchema):
    """Contrato de respuesta para un producto"""
    cod_pro: int
    nombre_pro: str
    descripcion_pro: Optional[str]
    stock_pro: int
    stock_pro_min: int
    cod_est_pro: int
    precio_pro: int
    estado_producto: Optional[str] = None
    impuestos: Optional[List[ImpuestoResponseContract]] = []
