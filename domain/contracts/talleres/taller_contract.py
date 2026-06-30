from typing import Optional

from pydantic import EmailStr

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
