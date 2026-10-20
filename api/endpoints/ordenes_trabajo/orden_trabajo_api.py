import logging
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.responses import Response
from domain.contracts.ordenes_trabajo.orden_trabajo_contract import (
    OrdenTrabajoCreateContract,
    OrdenTrabajoUpdateContract,
    OrdenTrabajoResponseContract,
    OrdenTrabajoResumenContract,
    CambiarEstadoContract,
    EntregarOrdenContract,
    AnularOrdenContract,
    OtEstadoResponseContract,
    HistorialEventoContract
)
from domain.contracts.ordenes_trabajo.detalle_orden_trabajo_contract import (
    DetalleOrdenTrabajoContract,
    DetalleOrdenUpdateContract
)
from domain.contracts.ordenes_trabajo.pago_orden_contract import (
    PagoOrdenCreateContract,
    PagoOrdenResponseContract,
    AnularPagoContract,
)
from domain.services.ordenes_trabajo.orden_trabajo_servicio import OrdenTrabajoServicio
from domain.services.ordenes_trabajo.historial_ot_servicio import HistorialOtServicio
from domain.services.ordenes_trabajo.pago_orden_servicio import PagoOrdenServicio
from infrastructure.dependencies.current_user import (
    get_current_usuario,
    require_admin,
    require_permiso,
    usuario_tiene_permiso,
)
from infrastructure.exceptions.domain_exception import DomainException

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/ordenes-trabajo",
    tags=["Ordenes de Trabajo"]
)


async def _verificar_permiso_no_cobro(cobrar_flags: List[bool], current: Optional[Dict]) -> None:
    """F1-06: marcar un ítem como 'no se cobra' (cortesía) exige un permiso
    específico -- solo se chequea si el body realmente trae algún cobrar_deto=False,
    no en cualquier POST/PATCH de la orden."""
    if any(not c for c in cobrar_flags):
        if not await usuario_tiene_permiso(current, "marcar_no_cobro:ordenes-trabajo"):
            raise DomainException(
                "No tienes permiso para marcar productos como 'no se cobra'",
                status.HTTP_403_FORBIDDEN,
            )


@router.get("", response_model=List[OrdenTrabajoResumenContract])
async def obtener_ordenes_trabajo():
    """Obtiene todas las ordenes de trabajo con informacion resumida"""
    servicio = OrdenTrabajoServicio()
    return await servicio.obtener_todas_ordenes()


@router.get("/estados", response_model=List[OtEstadoResponseContract])
async def obtener_estados_ot():
    """Obtiene todos los estados posibles de ordenes de trabajo"""
    servicio = OrdenTrabajoServicio()
    return await servicio.obtener_estados()


@router.get("/pendientes", response_model=List[dict])
async def obtener_ordenes_pendientes():
    """Obtiene todas las ordenes de trabajo pendientes de entrega"""
    servicio = OrdenTrabajoServicio()
    return await servicio.obtener_ordenes_pendientes()


@router.get("/cliente/{documento_cli}", response_model=List[OrdenTrabajoResumenContract])
async def obtener_ordenes_por_cliente(documento_cli: str):
    """Obtiene todas las ordenes de trabajo de un cliente especifico"""
    servicio = OrdenTrabajoServicio()
    return await servicio.obtener_ordenes_por_cliente(documento_cli)


@router.get("/moto/{placa_mot}", response_model=List[OrdenTrabajoResumenContract])
async def obtener_ordenes_por_moto(placa_mot: str):
    """Obtiene todas las ordenes de trabajo de una moto especifica"""
    servicio = OrdenTrabajoServicio()
    return await servicio.obtener_ordenes_por_moto(placa_mot)


@router.get(
    "/{consecutivo_ot}/generar-pdf",
    response_class=Response,
    responses={200: {"content": {"application/pdf": {}}, "description": "PDF de la orden de trabajo"}},
)
async def generar_pdf_orden_trabajo(consecutivo_ot: int):
    """Genera un PDF con la informacion completa de la orden de trabajo"""
    servicio = OrdenTrabajoServicio()

    # La validación de negocio (existencia, estado válido, tiene ítems) y la
    # personalización visual del taller (F1-09) viven en el servicio.
    try:
        nombre_archivo = f"orden_trabajo_{consecutivo_ot}.pdf"
        pdf_bytes = await servicio.generar_pdf_orden(consecutivo_ot)

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                # inline (no attachment): igual que el comprobante, para que se
                # abra directo en el navegador. Más cómodo para imprimir
                # desde el celular en el taller que forzar una descarga.
                "Content-Disposition": f"inline; filename={nombre_archivo}"
            }
        )
    except DomainException:
        raise
    except Exception:
        logger.exception("Error generando PDF de la orden %s", consecutivo_ot)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al generar el PDF"
        )


@router.get(
    "/{consecutivo_ot}/generar-comprobante",
    response_class=Response,
    responses={200: {"content": {"application/pdf": {}}, "description": "Comprobante POS en PDF"}},
)
async def generar_comprobante_orden_trabajo(consecutivo_ot: int):
    """Genera un PDF de comprobante de servicio en formato POS (ticket de 80mm)"""
    servicio = OrdenTrabajoServicio()

    # Generar el comprobante (toda la lógica de negocio está en el servicio,
    # en memoria: ver nota de seguridad en OrdenTrabajoPDFGenerator.generar_pdf)
    try:
        pdf_bytes = await servicio.generar_comprobante_servicio_pos(consecutivo_ot)
        nombre_archivo = f"comprobante_{consecutivo_ot}.pdf"

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"inline; filename={nombre_archivo}"
            }
        )
    except DomainException:
        raise
    except Exception:
        logger.exception("Error generando comprobante de la orden %s", consecutivo_ot)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al generar el comprobante"
        )


@router.get("/{consecutivo_ot}", response_model=OrdenTrabajoResponseContract)
async def obtener_orden_trabajo(consecutivo_ot: int):
    """Obtiene una orden de trabajo completa con todos sus detalles"""
    servicio = OrdenTrabajoServicio()
    return await servicio.obtener_orden_por_id(consecutivo_ot)


@router.post("", response_model=OrdenTrabajoResponseContract, status_code=status.HTTP_201_CREATED)
async def crear_orden_trabajo(
    orden: OrdenTrabajoCreateContract,
    _=Depends(require_permiso("crear_editar:ordenes-trabajo")),
    current: Optional[Dict] = Depends(get_current_usuario),
):
    """Crea una nueva orden de trabajo con sus productos/servicios.

    F1-01: orden rápida -- si no se manda documento_usu_rp_ot (recepcionista),
    por defecto es el usuario autenticado."""
    servicio = OrdenTrabajoServicio()
    documento_usuario = orden.documento_usu_rp_ot or (current and str(current.get("DOCUMENTO_USU")))
    if not documento_usuario:
        raise DomainException("No se pudo identificar al usuario autenticado", status.HTTP_401_UNAUTHORIZED)
    await _verificar_permiso_no_cobro([d.cobrar_deto for d in orden.detalles], current)
    return await servicio.crear_orden_trabajo(orden, documento_usuario)


@router.put("/{consecutivo_ot}", response_model=OrdenTrabajoResponseContract)
async def actualizar_orden_trabajo(
    consecutivo_ot: int,
    orden: OrdenTrabajoUpdateContract,
    _=Depends(require_permiso("crear_editar:ordenes-trabajo")),
):
    """Actualiza una orden de trabajo existente"""
    servicio = OrdenTrabajoServicio()
    return await servicio.actualizar_orden(consecutivo_ot, orden)


@router.patch("/{consecutivo_ot}/estado", response_model=OrdenTrabajoResponseContract)
async def cambiar_estado_orden(
    consecutivo_ot: int,
    estado: CambiarEstadoContract,
    _=Depends(require_permiso("crear_editar:ordenes-trabajo")),
):
    """Cambia el estado de una orden de trabajo"""
    servicio = OrdenTrabajoServicio()
    return await servicio.cambiar_estado(consecutivo_ot, estado)


@router.patch("/{consecutivo_ot}/entregar", response_model=OrdenTrabajoResponseContract)
async def entregar_orden_trabajo(
    consecutivo_ot: int,
    entrega: EntregarOrdenContract,
    _=Depends(require_permiso("crear_editar:ordenes-trabajo")),
):
    """Marca una orden de trabajo como entregada"""
    servicio = OrdenTrabajoServicio()
    return await servicio.entregar_orden(consecutivo_ot, entrega)


@router.patch("/{consecutivo_ot}/anular", response_model=OrdenTrabajoResponseContract)
async def anular_orden_trabajo(
    consecutivo_ot: int,
    anulacion: AnularOrdenContract,
    _=Depends(require_permiso("anular:ordenes-trabajo")),
    current: Optional[Dict] = Depends(get_current_usuario),
):
    """F1-05: anula una orden completa (motivo obligatorio), devuelve al
    inventario los bienes de la orden y deja constancia de quién/cuándo."""
    servicio = OrdenTrabajoServicio()
    documento_usuario = current and str(current.get("DOCUMENTO_USU"))
    if not documento_usuario:
        raise DomainException("No se pudo identificar al usuario autenticado", status.HTTP_401_UNAUTHORIZED)
    return await servicio.anular_orden(consecutivo_ot, anulacion.motivo, documento_usuario)


@router.get("/{consecutivo_ot}/historial", response_model=List[HistorialEventoContract])
async def obtener_historial_orden(
    consecutivo_ot: int,
    _=Depends(require_admin),
):
    """F1-05: historial de cambios de una orden (orden + su detalle), leído
    de audit_log. Solo el Admin del taller puede verlo."""
    if not await OrdenTrabajoServicio().repository.existe_orden(consecutivo_ot):
        raise DomainException(
            f"Orden de trabajo con consecutivo {consecutivo_ot} no encontrada",
            status.HTTP_404_NOT_FOUND
        )
    return await HistorialOtServicio().obtener_historial(consecutivo_ot)


@router.post("/{consecutivo_ot}/productos", response_model=OrdenTrabajoResponseContract)
async def agregar_producto_a_orden(
    consecutivo_ot: int,
    detalle: DetalleOrdenTrabajoContract,
    _=Depends(require_permiso("crear_editar:ordenes-trabajo")),
    current: Optional[Dict] = Depends(get_current_usuario),
):
    """Agrega un producto/servicio a una orden de trabajo existente"""
    servicio = OrdenTrabajoServicio()
    await _verificar_permiso_no_cobro([detalle.cobrar_deto], current)

    # Obtener la orden para usar el documento del recepcionista
    orden = await servicio.obtener_orden_por_id(consecutivo_ot)
    documento_usuario = orden.documento_recepcionista

    return await servicio.agregar_producto(consecutivo_ot, detalle, documento_usuario)


@router.patch("/{consecutivo_ot}/productos/{cod_pro}", response_model=OrdenTrabajoResponseContract)
async def actualizar_cantidad_producto(
    consecutivo_ot: int,
    cod_pro: int,
    detalle: DetalleOrdenUpdateContract,
    _=Depends(require_permiso("crear_editar:ordenes-trabajo")),
    current: Optional[Dict] = Depends(get_current_usuario),
):
    """
    Actualiza la cantidad de un producto en una orden de trabajo.
    Maneja automáticamente el ajuste de stock.
    """
    servicio = OrdenTrabajoServicio()
    await _verificar_permiso_no_cobro([detalle.cobrar_deto], current)
    return await servicio.actualizar_cantidad_producto(consecutivo_ot, cod_pro, detalle)


@router.delete("/{consecutivo_ot}/productos/{cod_pro}", response_model=OrdenTrabajoResponseContract)
async def eliminar_producto_de_orden(
    consecutivo_ot: int,
    cod_pro: int,
    _=Depends(require_permiso("eliminar_o_anular:ordenes-trabajo")),
):
    """Elimina un producto/servicio de una orden de trabajo"""
    servicio = OrdenTrabajoServicio()
    return await servicio.eliminar_producto(consecutivo_ot, cod_pro)


# ---- F1-07: pagos/abonos de una orden ----

@router.get("/{consecutivo_ot}/pagos", response_model=List[PagoOrdenResponseContract])
async def listar_pagos_orden(
    consecutivo_ot: int,
    _=Depends(require_permiso("ver:pagos-orden")),
):
    """Lista los abonos/pagos registrados a una orden (incluye anulados, con
    su marca anulado_pago, para que quede visible el historial completo)."""
    return await PagoOrdenServicio().listar_pagos_por_orden(consecutivo_ot)


@router.post(
    "/{consecutivo_ot}/pagos",
    response_model=PagoOrdenResponseContract,
    status_code=status.HTTP_201_CREATED,
)
async def registrar_pago_orden(
    consecutivo_ot: int,
    pago: PagoOrdenCreateContract,
    _=Depends(require_permiso("crear_editar:pagos-orden")),
    current: Optional[Dict] = Depends(get_current_usuario),
):
    """Registra un abono/pago a una orden."""
    documento_usuario = current and str(current.get("DOCUMENTO_USU"))
    if not documento_usuario:
        raise DomainException("No se pudo identificar al usuario autenticado", status.HTTP_401_UNAUTHORIZED)
    return await PagoOrdenServicio().registrar_pago(consecutivo_ot, pago, documento_usuario)


@router.patch("/{consecutivo_ot}/pagos/{cod_pago_orden}/anular", response_model=PagoOrdenResponseContract)
async def anular_pago_orden(
    consecutivo_ot: int,
    cod_pago_orden: int,
    anulacion: AnularPagoContract,
    _=Depends(require_permiso("eliminar_o_anular:pagos-orden")),
    current: Optional[Dict] = Depends(get_current_usuario),
):
    """Los pagos no se editan ni se borran -- se anulan con motivo obligatorio."""
    documento_usuario = current and str(current.get("DOCUMENTO_USU"))
    if not documento_usuario:
        raise DomainException("No se pudo identificar al usuario autenticado", status.HTTP_401_UNAUTHORIZED)
    return await PagoOrdenServicio().anular_pago(cod_pago_orden, anulacion.motivo, documento_usuario)
