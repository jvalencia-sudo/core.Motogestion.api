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
    salen en el comprobante y en la orden (PDF). nombre/NIT/correo NO están
    acá -- son de solo lectura (ver TallerConfigResponse): nunca llegan por
    este contrato de entrada.

    - modo_mano_obra: HORAS (tarifa fija, tarifa_hora_pred) o LIBRE (se
      define el valor en cada orden).
    - texto_pie_comprobante: línea libre que se imprime al final del
      comprobante de servicio (ej. política de garantía, horario de atención).
    - nombre_comercial_tal: si no se define, la orden usa nombre_tal (F1-09).
    - texto_condiciones_tal / texto_pie_tal: condiciones y pie de la ORDEN
      (carta) -- distintos de texto_pie_comprobante (tirilla POS 80mm): un
      texto de 1500 caracteres no cabe en un ticket de 80mm.
    """
    modo_mano_obra: Literal["HORAS", "LIBRE"]
    tarifa_hora_pred: int = Field(0, ge=0, description="Tarifa por hora por defecto (modo HORAS)")
    telefono_tal: Optional[str] = Field(None, max_length=20)
    direccion_tal: Optional[str] = Field(None, max_length=200)
    texto_pie_comprobante: Optional[str] = Field(None, max_length=300)
    nombre_comercial_tal: Optional[str] = Field(None, max_length=150)
    whatsapp_tal: Optional[str] = Field(None, max_length=20)
    color_principal_tal: str = Field(
        "#00B06E", pattern=r"^#[0-9A-Fa-f]{6}$", description="Color principal en hexadecimal"
    )
    texto_condiciones_tal: Optional[str] = Field(None, max_length=1500)
    texto_pie_tal: Optional[str] = Field(None, max_length=200)
    mostrar_precios_unitarios_tal: bool = True
    mostrar_mecanico_tal: bool = True
    mostrar_firma_cliente_tal: bool = False
    # F2-01: ¿se muestran ítems y total en el link público de estado, o solo
    # el estado? (ej. un taller que no quiere mostrar precios por WhatsApp
    # antes de hablar con el cliente puede apagarlo).
    mostrar_detalle_publico_tal: bool = True
    # F2-02: horario de atención, texto libre, visible en el link público.
    horario_atencion_tal: Optional[str] = Field(None, max_length=300)
    # F2-03: aprobación de cotización ANTES de reparar -- opcional por
    # taller, default apagado (nadie pierde su flujo actual sin pedirlo).
    exige_aprobacion_cotizacion_tal: bool = False


class TallerConfigResponse(TallerConfigContract):
    """Respuesta de GET/PUT /talleres/config: lo editable más lo de solo
    lectura (nombre/NIT/correo -- correo es la llave anti-abuso del trial,
    cambiarlo requiere soporte)."""
    nombre_tal: str
    nit_tal: Optional[str] = None
    correo_tal: Optional[str] = None
    tiene_logo: bool = False


class VistaPreviaOrdenContract(BaseSchema):
    """Body de POST /talleres/vista-previa-pdf: la misma personalización de
    TallerConfigContract (sin guardar) para previsualizar la orden mientras
    se edita 'Mi taller'. El logo que se usa es el YA guardado (el logo se
    sube aparte, de inmediato, no se previsualiza sin subir)."""
    nombre_comercial_tal: Optional[str] = Field(None, max_length=150)
    whatsapp_tal: Optional[str] = Field(None, max_length=20)
    color_principal_tal: str = Field("#00B06E", pattern=r"^#[0-9A-Fa-f]{6}$")
    texto_condiciones_tal: Optional[str] = Field(None, max_length=1500)
    texto_pie_tal: Optional[str] = Field(None, max_length=200)
    mostrar_precios_unitarios_tal: bool = True
    mostrar_mecanico_tal: bool = True
    mostrar_firma_cliente_tal: bool = False


class LogoSubidoResponse(BaseSchema):
    mensaje: str
