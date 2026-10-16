from datetime import datetime
from typing import List, Optional

from pydantic import Field

from domain.contracts.base_contract import BaseContractSchema


class TallerListadoContract(BaseContractSchema):
    """Una fila de la lista de talleres del panel de super-admin (F0-14)."""
    cod_taller: int
    nombre_tal: str
    nit_tal: Optional[str] = None
    correo_tal: Optional[str] = None
    telefono_tal: Optional[str] = None
    fecha_creacion_tal: Optional[datetime] = None
    estado_tal: str
    dias_restantes: Optional[int] = None
    precio_susc_tal: Optional[int] = None
    es_fundador: bool = False
    ultimo_pago_fecha: Optional[str] = None
    ordenes_7d: int = 0
    ordenes_30d: int = 0
    usuarios_activos: int = 0
    ultima_actividad: Optional[str] = None


class UsuarioTallerContract(BaseContractSchema):
    documento_usu: str
    nombre_completo: str
    rol: str
    ultimo_ingreso: Optional[str] = None


class PagoHistorialContract(BaseContractSchema):
    cod_pago: int
    nombre_plan: str
    monto: int
    estado: str
    medio: str
    detalle_medio: Optional[str] = None
    fecha: str


class NotaTallerContract(BaseContractSchema):
    id: int
    autor: str
    fecha: str
    texto: str


class TallerDetalleContract(BaseContractSchema):
    taller: TallerListadoContract
    pagos: List[PagoHistorialContract]
    usuarios: List[UsuarioTallerContract]
    notas: List[NotaTallerContract]


class CrearNotaContract(BaseContractSchema):
    texto: str = Field(..., min_length=1)
