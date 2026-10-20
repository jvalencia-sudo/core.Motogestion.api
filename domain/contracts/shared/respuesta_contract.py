from typing import List, Optional

from pydantic import BaseModel

from domain.models.auth.user_model import UserModel


class MensajeResponseContract(BaseModel):
    message: str


class OperacionResponseContract(BaseModel):
    success: bool
    message: str


class PerfilCreadoResponseContract(OperacionResponseContract):
    cod_prf: Optional[int] = None


class InvitacionResponseContract(BaseModel):
    correo: str
    documento_usu: str
    es_admin: bool


class UsuariosPaginadosResponseContract(BaseModel):
    users: List[UserModel]
    total: int
    limit: int
    offset: int
    total_pages: int


class EntradaInventarioResponseContract(BaseModel):
    cod_pro: int
    stock_nuevo: float


class TomaFisicaResponseContract(BaseModel):
    ajustados: int


class MarcaEliminadaResponseContract(MensajeResponseContract):
    cod_mar: int


class ProductoEstadoResponseContract(MensajeResponseContract):
    cod_pro: int


class CambioEstadoTableroResponseContract(BaseModel):
    consecutivo_ot: int
    cod_estado: int


class WompiWebhookResponseContract(BaseModel):
    ok: bool
    ignored: Optional[str] = None
    estado: Optional[str] = None


class MetricasTallerContract(BaseModel):
    ordenes_7d: int = 0
    ordenes_30d: int = 0
    usuarios_activos: int = 0
    ultima_actividad: Optional[str] = None
