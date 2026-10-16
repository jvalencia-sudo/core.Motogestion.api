from typing import Optional, Literal

from pydantic import EmailStr, Field

from domain.models.base_model import BaseSchema


class TallerRegistroContract(BaseSchema):
    """Datos para registrar un taller nuevo (desde la landing pública)."""
    nombre_tal: str
    correo: EmailStr        # correo del dueño (queda pre-registrado para el login)
    nombre_dueno: str
    nit_tal: Optional[str] = None


class TallerRegistroResponse(BaseSchema):
    cod_taller: int
    nombre_tal: str
    correo: str


class TallerUpdateContract(BaseSchema):
    """Edición de un taller (para la vista de gestión). Todos opcionales."""
    nombre_tal: Optional[str] = None
    nit_tal: Optional[str] = None
    correo_tal: Optional[str] = None
    telefono_tal: Optional[str] = None
    estado_tal: Optional[str] = None      # prueba | activo | suspendido
    plan_tal: Optional[str] = None


class TallerSuscripcionContract(BaseSchema):
    """Estado de suscripción del taller (para el front: banner/gating y la
    vista de 'Suscripción' en Administración)."""
    estado: str                       # prueba | activo | suspendido
    plan: Optional[str] = None
    precio: Optional[int] = None      # precio mensual pactado (None si aún no paga)
    fecha_fin: Optional[str] = None   # ISO date
    dias_restantes: Optional[int] = None
    vencido: bool = False
    miembro_desde: Optional[str] = None  # ISO date (fecha_creacion_tal)


class TallerConfigContract(BaseSchema):
    """Configuración propia del taller ('Mi taller'): mano de obra + datos que
    salen en el comprobante. nombre/NIT/correo NO están acá -- son de solo
    lectura (ver TallerConfigResponse), igual que cod_rol_prf en los roles:
    nunca llegan por este contrato de entrada.

    - modo_mano_obra: HORAS (tarifa fija, tarifa_hora_pred) o LIBRE (se
      define el valor en cada orden).
    - texto_pie_comprobante: línea libre que se imprime al final del
      comprobante de servicio (ej. política de garantía, horario de atención).
    - dias_garantia_pred: días de garantía por defecto cuando una orden se
      entrega sin fecha de garantía explícita.
    """
    modo_mano_obra: Literal["HORAS", "LIBRE"]
    tarifa_hora_pred: int = Field(0, ge=0, description="Tarifa por hora por defecto (modo HORAS)")
    telefono_tal: Optional[str] = Field(None, max_length=20)
    direccion_tal: Optional[str] = Field(None, max_length=200)
    texto_pie_comprobante: Optional[str] = Field(None, max_length=300)
    dias_garantia_pred: int = Field(30, ge=0, le=365)


class TallerConfigResponse(TallerConfigContract):
    """Respuesta de GET/PUT /talleres/config: lo editable más lo de solo
    lectura (nombre/NIT/correo -- correo es la llave anti-abuso del trial,
    cambiarlo requiere soporte)."""
    nombre_tal: str
    nit_tal: Optional[str] = None
    correo_tal: Optional[str] = None
