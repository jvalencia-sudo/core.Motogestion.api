from typing import Dict, List

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status

from domain.contracts.talleres.taller_contract import (
    LogoSubidoResponse,
    TallerConfigContract,
    TallerConfigResponse,
    TallerRegistroContract,
    TallerRegistroResponse,
    TallerSuscripcionContract,
    TallerUpdateContract,
    VistaPreviaOrdenContract,
)
from domain.models.talleres.taller_model import TallerModel
from domain.services.talleres.taller_servicio import TallerServicio
from infrastructure.dependencies.current_user import (
    get_current_usuario,
    require_admin,
    require_super_admin,
)

router = APIRouter()


@router.post("", response_model=TallerRegistroResponse, status_code=status.HTTP_201_CREATED)
async def registrar_taller(contract: TallerRegistroContract):
    """
    Registra un taller nuevo (endpoint público para la landing).

    Crea el taller, su usuario dueño (pre-registrado por correo) y catálogos base.
    El dueño inicia sesión luego con ese correo (el login es cerrado a usuarios registrados).
    """
    return await TallerServicio().registrar(contract)


# Config de mano de obra del PROPIO taller (dueño/Admin). El taller se toma del
# token (no de un path param): 'talleres' no tiene RLS, así que el tenant debe
# venir del usuario autenticado. Se declara antes de las rutas /{cod_taller}.

@router.get("/config", response_model=TallerConfigResponse)
async def obtener_config(current: Dict = Depends(require_admin)):
    """Obtiene la configuración del taller del usuario (mano de obra + comprobante)."""
    return await TallerServicio().obtener_config(current.get("COD_TALLER"))


@router.put("/config", response_model=TallerConfigResponse)
async def actualizar_config(
    contract: TallerConfigContract,
    current: Dict = Depends(require_admin),
):
    """Actualiza la config del taller: mano de obra, teléfono/dirección, pie del
    comprobante y días de garantía por defecto. nombre/NIT/correo no se tocan acá."""
    return await TallerServicio().actualizar_config(current.get("COD_TALLER"), contract)


@router.post("/logo", response_model=LogoSubidoResponse)
async def subir_logo(
    file: UploadFile = File(...),
    current: Dict = Depends(require_admin),
):
    """Sube (o reemplaza) el logo del taller para la orden/comprobante (F1-09).
    PNG/JPG/WebP, máx. 2MB -- se valida y redimensiona en el servicio."""
    contenido = await file.read()
    await TallerServicio().subir_logo(
        current.get("COD_TALLER"), contenido, file.content_type
    )
    return LogoSubidoResponse(mensaje="Logo actualizado correctamente.")


@router.get(
    "/logo",
    responses={200: {"content": {"image/png": {}}}, 404: {"description": "Sin logo configurado"}},
)
async def obtener_logo(current: Dict = Depends(require_admin)):
    """Devuelve el logo guardado del taller (binario), o 404 si no hay."""
    logo = await TallerServicio().obtener_logo(current.get("COD_TALLER"))
    if not logo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="El taller no tiene logo configurado.")
    return Response(content=logo.get("LOGO"), media_type=logo.get("CONTENT_TYPE") or "image/png")


@router.post(
    "/vista-previa-pdf",
    responses={200: {"content": {"application/pdf": {}}, "description": "PDF de ejemplo con la personalización del formulario"}},
)
async def vista_previa_pdf(
    contract: VistaPreviaOrdenContract,
    current: Dict = Depends(require_admin),
):
    """Genera el PDF de una orden de EJEMPLO con la personalización del
    formulario, sin guardar nada (F1-09: vista previa en 'Mi taller')."""
    pdf_bytes = await TallerServicio().vista_previa_pdf(current.get("COD_TALLER"), contract)
    return Response(content=pdf_bytes, media_type="application/pdf")


@router.get("/suscripcion", response_model=TallerSuscripcionContract)
async def obtener_suscripcion(current: Dict = Depends(get_current_usuario)):
    """Estado de suscripción del taller del usuario (para banner/gating en el front)."""
    if current is None:
        from infrastructure.exceptions.domain_exception import DomainException
        raise DomainException("No autenticado", status.HTTP_401_UNAUTHORIZED)
    return await TallerServicio().obtener_suscripcion(current.get("COD_TALLER"))


# Endpoints de gestión: solo super-admin (Admin del taller plataforma) puede
# listar/ver/editar TODOS los talleres.

@router.get("", response_model=List[TallerModel], dependencies=[Depends(require_super_admin)])
async def listar_talleres():
    """Lista todos los talleres (vista de gestión / super-admin)."""
    return await TallerServicio().listar()


@router.get("/{cod_taller}", response_model=TallerModel, dependencies=[Depends(require_super_admin)])
async def obtener_taller(cod_taller: int):
    """Obtiene un taller por su código."""
    return await TallerServicio().obtener(cod_taller)


@router.put("/{cod_taller}", response_model=TallerModel, dependencies=[Depends(require_super_admin)])
async def actualizar_taller(cod_taller: int, contract: TallerUpdateContract):
    """Actualiza los datos / estado / plan de un taller."""
    return await TallerServicio().actualizar(cod_taller, contract)
