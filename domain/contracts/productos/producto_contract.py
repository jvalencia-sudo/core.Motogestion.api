from typing import Optional, List, Literal
from decimal import Decimal
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


class ComponenteContract(BaseContractSchema):
    """Un componente de un paquete/combo (producto incluido + cantidad)."""
    cod_pro_comp: int = Field(..., gt=0, description="Código del producto incluido")
    cantidad_comp: Decimal = Field(..., gt=0, description="Cantidad del componente en el paquete")


class ComponenteResponseContract(BaseContractSchema):
    """Componente de un paquete, con datos del producto incluido."""
    cod_pro_comp: int
    nombre_pro: str
    tipo_pro: str
    cantidad_comp: Decimal


class ProductoCreateContract(BaseContractSchema):
    """Contrato para crear un producto con sus impuestos"""
    nombre_pro: str = Field(..., min_length=1, max_length=70, description="Nombre del producto")
    descripcion_pro: str = Field(..., min_length=1, max_length=500, description="Descripción del producto")
    # BIEN maneja stock; SERVICIO (mano de obra) no; PAQUETE es un combo de precio fijo.
    tipo_pro: Literal["BIEN", "SERVICIO", "PAQUETE"] = Field("BIEN", description="Tipo: BIEN, SERVICIO o PAQUETE")
    stock_pro: Optional[int] = Field(None, ge=0, description="Stock actual (solo BIEN)")
    stock_pro_min: Optional[int] = Field(None, ge=0, description="Stock mínimo (solo BIEN)")
    precio_pro: int = Field(..., gt=0, description="Precio del producto (debe ser mayor a 0)")
    impuestos: Optional[List[ImpuestoProductoContract]] = Field(default=[], description="Lista de impuestos a aplicar")
    # Componentes de la "receta" cuando tipo_pro == PAQUETE.
    componentes: Optional[List[ComponenteContract]] = Field(default=[], description="Componentes del paquete (solo PAQUETE)")


class ProductoUpdateContract(BaseContractSchema):
    """Contrato para actualizar un producto"""
    nombre_pro: Optional[str] = Field(None, min_length=1, max_length=70, description="Nombre del producto")
    descripcion_pro: Optional[str] = Field(None, min_length=1, max_length=500, description="Descripción del producto")
    tipo_pro: Optional[Literal["BIEN", "SERVICIO", "PAQUETE"]] = Field(None, description="Tipo: BIEN, SERVICIO o PAQUETE")
    stock_pro: Optional[int] = Field(None, ge=0, description="Stock actual (solo BIEN)")
    stock_pro_min: Optional[int] = Field(None, ge=0, description="Stock mínimo (solo BIEN)")
    precio_pro: Optional[int] = Field(None, gt=0, description="Precio del producto (debe ser mayor a 0)")
    impuestos: Optional[List[ImpuestoProductoContract]] = Field(None, description="Lista de impuestos a aplicar")
    componentes: Optional[List[ComponenteContract]] = Field(None, description="Componentes del paquete (solo PAQUETE, reemplaza los existentes)")


class ProductoResponseContract(BaseContractSchema):
    """Contrato de respuesta para un producto"""
    cod_pro: int
    nombre_pro: str
    descripcion_pro: Optional[str]
    tipo_pro: str = "BIEN"
    stock_pro: Optional[int] = None
    stock_pro_min: Optional[int] = None
    cod_est_pro: int
    precio_pro: int
    estado_producto: Optional[str] = None
    impuestos: Optional[List[ImpuestoResponseContract]] = []
    componentes: Optional[List[ComponenteResponseContract]] = []
