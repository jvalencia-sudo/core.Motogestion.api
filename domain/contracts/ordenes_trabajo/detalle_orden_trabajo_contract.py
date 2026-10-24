from typing import Optional
from datetime import datetime
from decimal import Decimal
from pydantic import Field, model_validator
from domain.contracts.base_contract import BaseContractSchema


class DetalleOrdenTrabajoContract(BaseContractSchema):
    """Contrato para agregar un producto a una orden de trabajo"""
    cod_pro_deto: int = Field(..., gt=0, description="Codigo del producto")
    # Decimal para permitir fracciones (p.ej. 1.5 h de mano de obra o 1.5 litros).
    cantidad_deto: Decimal = Field(..., gt=0, description="Cantidad (siempre positiva; permite decimales)")
    valor_unitario_deto: Optional[int] = Field(None, gt=0, description="Valor unitario (si no se provee, se toma del producto)")
    cobrar_deto: bool = Field(True, description="Si es false: no se factura, pero SÍ descuenta stock (cortesía)")
    motivo_no_cobro_deto: Optional[str] = Field(None, max_length=200, description="Obligatorio si cobrar_deto es false")

    @model_validator(mode="after")
    def _motivo_obligatorio_si_no_cobra(self):
        if not self.cobrar_deto and not (self.motivo_no_cobro_deto and self.motivo_no_cobro_deto.strip()):
            raise ValueError("motivo_no_cobro_deto es obligatorio cuando cobrar_deto es false")
        return self


class DetalleOrdenTrabajoResponseContract(BaseContractSchema):
    """Contrato de respuesta para un detalle de orden de trabajo"""
    consecutivo_ot_deto: int
    cod_pro_deto: int
    nombre_pro: str
    descripcion_pro: Optional[str] = None
    cantidad_deto: Decimal
    valor_unitario_deto: int
    cobrar_deto: bool
    motivo_no_cobro_deto: Optional[str] = None
    subtotal: float
    fecha_confirmacion_deto: Optional[datetime] = None
    usuario_confirmacion: str
    estado_producto: str
    # F2-01 fase 2: BIEN/SERVICIO/PAQUETE, para agrupar la cotización pública
    # en "Repuestos"/"Mano de obra". Default solo para no romper la orden de
    # ejemplo de la vista previa del PDF (infrastructure/utils/orden_ejemplo.py).
    tipo_pro: str = "BIEN"
    # F2-02: retirar un ítem ya no lo borra -- lo marca con motivo. La fila
    # sigue viéndose (tachada) tanto en la vista interna como en el link
    # público.
    retirado: bool = False
    motivo_retiro: Optional[str] = None


class RetirarProductoContract(BaseContractSchema):
    """F2-02: retirar un producto de una orden (reemplaza el DELETE físico).
    Motivo obligatorio, mismo criterio que anular una orden (F1-05)."""
    motivo: str = Field(..., min_length=1, max_length=200, description="Motivo del retiro, obligatorio")


class GuardarDiagnosticoContract(BaseContractSchema):
    """F2-02: diagnóstico del mecánico que ve el cliente final en el link
    público -- separado de observacion_ot (interno). Vacío = lo borra."""
    texto: str = Field("", max_length=2000)


class DetalleOrdenUpdateContract(BaseContractSchema):
    """Contrato para actualizar cantidad de un producto en orden de trabajo"""
    cantidad_deto: Decimal = Field(..., gt=0, description="Nueva cantidad (siempre positiva; permite decimales)")
    cobrar_deto: bool = Field(True, description="Si es false: no se factura, pero SÍ descuenta stock (cortesía)")
    motivo_no_cobro_deto: Optional[str] = Field(None, max_length=200, description="Obligatorio si cobrar_deto es false")

    @model_validator(mode="after")
    def _motivo_obligatorio_si_no_cobra(self):
        if not self.cobrar_deto and not (self.motivo_no_cobro_deto and self.motivo_no_cobro_deto.strip()):
            raise ValueError("motivo_no_cobro_deto es obligatorio cuando cobrar_deto es false")
        return self
