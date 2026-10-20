from typing import Optional, List, Dict, Any
from datetime import date, datetime
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
    # F1-01: ambos opcionales -- una orden rápida se abre solo con placa, km y
    # motivo. Si no se manda documento_usu_rp_ot, el endpoint usa el usuario
    # autenticado. El mecánico se asigna después.
    documento_usu_rp_ot: Optional[str] = Field(None, min_length=8, max_length=11, description="Documento del recepcionista (default: usuario autenticado)")
    documento_usu_mc_ot: Optional[str] = Field(None, min_length=8, max_length=11, description="Documento del mecanico (se puede asignar después)")
    observacion_cli_ot: Optional[str] = Field(None, max_length=500, description="Observacion del cliente")
    observacion_ot: Optional[str] = Field(None, max_length=500, description="Observacion interna")
    fecha_entrega_ot: Optional[date] = Field(None, description="Fecha estimada de entrega")
    cod_ot_est_ot: Optional[int] = Field(default=1, ge=1, le=6, description="Estado de la orden (1=Pendiente, 2=En Proceso, 3=Finalizada, 4=Entregada, 6=Garantia)")
    detalles: List[DetalleOrdenTrabajoContract] = Field(default=[], description="Productos/servicios de la orden")

    @field_validator('fecha_entrega_ot', mode='before')
    @classmethod
    def empty_string_to_none(cls, v):
        """Convierte strings vacíos a None para campos de fecha"""
        if v == '' or v is None:
            return None
        return v

    @field_validator('cod_ot_est_ot')
    @classmethod
    def no_crear_directo_en_anulada(cls, v):
        """F1-05: Anulada (5) solo se alcanza vía PATCH .../anular (motivo
        obligatorio + devolución de stock) -- nunca directo al crear."""
        if v == 5:
            raise ValueError(
                "No se puede crear una orden ya anulada. Usa el endpoint de anular una vez creada."
            )
        return v


class OrdenTrabajoUpdateContract(BaseContractSchema):
    """Contrato para actualizar una orden de trabajo (todos los campos opcionales)"""
    fecha_entrega_ot: Optional[date] = None
    observacion_ot: Optional[str] = Field(None, max_length=500)
    cod_ot_est_ot: Optional[int] = Field(None, ge=1, le=6)
    documento_usu_rp_ot: Optional[str] = Field(None, min_length=8, max_length=11, description="Documento del recepcionista")
    documento_usu_mc_ot: Optional[str] = Field(None, min_length=8, max_length=11, description="Documento del mecanico")

    @field_validator('fecha_entrega_ot', mode='before')
    @classmethod
    def empty_string_to_none(cls, v):
        """Convierte strings vacíos a None para campos de fecha"""
        if v == '' or v is None:
            return None
        return v

    @field_validator('cod_ot_est_ot')
    @classmethod
    def no_anular_via_update(cls, v):
        """F1-05: Anulada (5) solo se alcanza vía PATCH .../anular (motivo
        obligatorio + devolución de stock) -- nunca por este PUT genérico."""
        if v == 5:
            raise ValueError(
                "No se puede anular una orden por esta vía. Usa el endpoint de anular."
            )
        return v


class CambiarEstadoContract(BaseContractSchema):
    """Contrato para cambiar el estado de una orden de trabajo"""
    cod_ot_est_ot: int = Field(..., ge=1, le=4, description="Codigo del nuevo estado (1=Pendiente, 2=En Proceso, 3=Finalizada, 4=Entregada)")
    # F1-07: el tablero (arrastrar y soltar) usa este endpoint para mover una
    # orden a Entregada -- si queda saldo pendiente, el backend lo rechaza
    # salvo que el front confirme explícitamente "entregar a crédito".
    confirmar_credito: bool = Field(False, description="Confirma entregar con saldo pendiente (a crédito)")


class EntregarOrdenContract(BaseContractSchema):
    """Contrato para marcar una orden como entregada"""
    kilometraje_salida_ot: Optional[int] = Field(None, gt=0, description="Kilometraje de salida")
    # F1-07: si queda saldo pendiente, el backend rechaza la entrega salvo
    # que el front confirme explícitamente "entregar a crédito".
    confirmar_credito: bool = Field(False, description="Confirma entregar con saldo pendiente (a crédito)")


class AnularOrdenContract(BaseContractSchema):
    """Contrato para anular una orden de trabajo completa (F1-05). El motivo
    es obligatorio -- queda en ordenes_trabajo y en audit_log."""
    motivo: str = Field(..., min_length=5, max_length=500, description="Motivo de la anulación")

    @field_validator('motivo')
    @classmethod
    def no_solo_espacios(cls, v):
        if not v.strip():
            raise ValueError("El motivo no puede estar vacío")
        return v.strip()


class OrdenTrabajoResponseContract(BaseContractSchema):
    """Contrato de respuesta para una orden de trabajo completa"""
    consecutivo_ot: int
    fecha_elaboracion_ot: date
    fecha_entrega_ot: Optional[date] = None
    kilometraje_ingreso_ot: int
    kilometraje_salida_ot: Optional[int] = None
    observacion_cli_ot: Optional[str] = None
    observacion_ot: Optional[str] = None
    fecha_fin_garantia_ot: Optional[date] = None

    # Anulación (F1-05)
    motivo_anulacion_ot: Optional[str] = None
    fecha_anulacion_ot: Optional[datetime] = None
    documento_usu_anulacion_ot: Optional[str] = None

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
    documento_mecanico: Optional[str] = None
    mecanico: Optional[str] = None

    # Estado
    estado_ot: str
    cod_ot_est_ot: int

    # Detalles y totales
    detalles: Optional[List[DetalleOrdenTrabajoResponseContract]] = []
    total_items: Optional[int] = 0
    subtotal_productos: Optional[float] = 0.0
    total_impuestos: Optional[float] = 0.0
    total_ot: Optional[float] = 0.0
    # F1-07: pagado/saldo (excluye ítems no cobrados y pagos anulados)
    total_pagado: Optional[float] = 0.0
    saldo_ot: Optional[float] = 0.0


class OrdenTrabajoResumenContract(BaseContractSchema):
    """Contrato de respuesta resumida para listados"""
    consecutivo_ot: int
    fecha_elaboracion_ot: date
    fecha_entrega_ot: Optional[date] = None
    placa_mot: str
    nombre_completo_cliente: str
    telefono_cli: str
    estado_ot: str
    cod_ot_est_ot: int
    mecanico: Optional[str] = None
    # F1-02: para el historial del buscador de placa (fecha, kilometraje, trabajos).
    kilometraje_ingreso_ot: int
    trabajos: Optional[str] = None
    total_ot: Optional[float] = 0.0
    # F1-07: para la columna/filtro "con saldo pendiente" del listado.
    saldo_ot: Optional[float] = 0.0


class OtEstadoResponseContract(BaseContractSchema):
    """Contrato de respuesta para estados de OT"""
    cod_ot_est: int
    nombre_ot_est: str


class HistorialEventoContract(BaseContractSchema):
    """Un evento de audit_log relacionado con la orden (ella misma o su
    detalle), para la pantalla 'Historial de cambios' (F1-05)."""
    fecha: datetime
    usuario: str
    tabla: str
    evento: str  # "Creado" | "Editado" | "Eliminado"
    valor_anterior: Optional[Dict[str, Any]] = None
    valor_nuevo: Optional[Dict[str, Any]] = None
