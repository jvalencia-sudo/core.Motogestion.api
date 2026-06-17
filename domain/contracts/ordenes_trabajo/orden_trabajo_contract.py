from typing import Optional, List
from datetime import date
from pydantic import Field, field_validator
from domain.contracts.base_contract import BaseContractSchema
from domain.contracts.ordenes_trabajo.detalle_orden_trabajo_contract import (
    DetalleOrdenTrabajoContract,
    DetalleOrdenTrabajoResponseContract
)


class OrdenTrabajoCreateContract(BaseContractSchema):
    """Contrato para crear una orden de trabajo"""
    placa_mot_ot: str = Field(..., min_length=5, max_length=6, description="Placa de la moto")
    kilometraje_ingreso_ot: int = Field(..., gt=0, description="Kilometraje de ingreso")
    documento_usu_rp_ot: str = Field(..., min_length=8, max_length=11, description="Documento del recepcionista")
    documento_usu_mc_ot: str = Field(..., min_length=8, max_length=11, description="Documento del mecanico")
    observacion_cli_ot: Optional[str] = Field(None, max_length=500, description="Observacion del cliente")
    observacion_ot: Optional[str] = Field(None, max_length=500, description="Observacion interna")
    fecha_entrega_ot: Optional[date] = Field(None, description="Fecha estimada de entrega")
    fecha_fin_garantia_ot: Optional[date] = Field(None, description="Fecha fin de garantia")
    cod_ot_est_ot: Optional[int] = Field(default=1, ge=1, le=6, description="Estado de la orden (1=Pendiente, 2=En Proceso, 3=Finalizada, 4=Entregada, 6=Garantia)")
    detalles: List[DetalleOrdenTrabajoContract] = Field(default=[], description="Productos/servicios de la orden")

    @field_validator('fecha_entrega_ot', 'fecha_fin_garantia_ot', mode='before')
    @classmethod
    def empty_string_to_none(cls, v):
        """Convierte strings vacíos a None para campos de fecha"""
        if v == '' or v is None:
            return None
        return v


class OrdenTrabajoUpdateContract(BaseContractSchema):
    """Contrato para actualizar una orden de trabajo (todos los campos opcionales)"""
    fecha_entrega_ot: Optional[date] = None
    observacion_ot: Optional[str] = Field(None, max_length=500)
    cod_ot_est_ot: Optional[int] = Field(None, ge=1, le=6)
    fecha_fin_garantia_ot: Optional[date] = None
    documento_usu_rp_ot: Optional[str] = Field(None, min_length=8, max_length=11, description="Documento del recepcionista")
    documento_usu_mc_ot: Optional[str] = Field(None, min_length=8, max_length=11, description="Documento del mecanico")

    @field_validator('fecha_entrega_ot', 'fecha_fin_garantia_ot', mode='before')
    @classmethod
    def empty_string_to_none(cls, v):
        """Convierte strings vacíos a None para campos de fecha"""
        if v == '' or v is None:
            return None
        return v


class CambiarEstadoContract(BaseContractSchema):
    """Contrato para cambiar el estado de una orden de trabajo"""
    cod_ot_est_ot: int = Field(..., ge=1, le=4, description="Codigo del nuevo estado (1=Pendiente, 2=En Proceso, 3=Finalizada, 4=Entregada)")


class EntregarOrdenContract(BaseContractSchema):
    """Contrato para marcar una orden como entregada"""
    kilometreje_salida_ot: Optional[int] = Field(None, gt=0, description="Kilometraje de salida")


class OrdenTrabajoResponseContract(BaseContractSchema):
    """Contrato de respuesta para una orden de trabajo completa"""
    consecutivo_ot: int
    fecha_elaboracion_ot: date
    fecha_entrega_ot: Optional[date] = None
    kilometraje_ingreso_ot: int
    observacion_cli_ot: Optional[str] = None
    observacion_ot: Optional[str] = None
    fecha_fin_garantia_ot: Optional[date] = None

    # Informacion de la moto
    placa_mot: str
    modelo_mot: int
    color_mot: str
    cilindraje_mot: int
    marca_moto: str

    # Informacion del cliente
    documento_cli: str
    nombre_completo_cliente: str
    telefono_cli: str
    correo_cli: str
    direccion_cli: Optional[str] = None

    # Informacion de usuarios
    documento_recepcionista: str
    recepcionista: str
    documento_mecanico: str
    mecanico: str

    # Estado
    estado_ot: str
    cod_ot_est_ot: int

    # Detalles y totales
    detalles: Optional[List[DetalleOrdenTrabajoResponseContract]] = []
    total_items: Optional[int] = 0
    subtotal_productos: Optional[float] = 0.0
    total_impuestos: Optional[float] = 0.0
    total_ot: Optional[float] = 0.0


class OrdenTrabajoResumenContract(BaseContractSchema):
    """Contrato de respuesta resumida para listados"""
    consecutivo_ot: int
    fecha_elaboracion_ot: date
    fecha_entrega_ot: Optional[date] = None
    placa_mot: str
    nombre_completo_cliente: str
    telefono_cli: str
    estado_ot: str
    mecanico: str
    total_ot: Optional[float] = 0.0


class OtEstadoResponseContract(BaseContractSchema):
    """Contrato de respuesta para estados de OT"""
    cod_ot_est: int
    nombre_ot_est: str
