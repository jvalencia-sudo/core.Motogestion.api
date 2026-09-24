import logging
from typing import List
from fastapi import APIRouter, status, HTTPException
from fastapi.responses import Response
from domain.contracts.ordenes_trabajo.orden_trabajo_contract import (
    OrdenTrabajoCreateContract,
    OrdenTrabajoUpdateContract,
    OrdenTrabajoResponseContract,
    OrdenTrabajoResumenContract,
    CambiarEstadoContract,
    EntregarOrdenContract,
    OtEstadoResponseContract
)
from domain.contracts.ordenes_trabajo.detalle_orden_trabajo_contract import (
    DetalleOrdenTrabajoContract,
    DetalleOrdenUpdateContract
)
from domain.services.ordenes_trabajo.orden_trabajo_servicio import OrdenTrabajoServicio
from infrastructure.exceptions.domain_exception import DomainException
from infrastructure.utils.pdf_generator import OrdenTrabajoPDFGenerator

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/ordenes-trabajo",
    tags=["Ordenes de Trabajo"]
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


@router.get("/{consecutivo_ot}/generar-pdf")
async def generar_pdf_orden_trabajo(consecutivo_ot: int):
    """Genera un PDF con la informacion completa de la orden de trabajo"""
    servicio = OrdenTrabajoServicio()

    # La validación de negocio (existencia, estado válido, tiene ítems) vive en el servicio.
    orden = await servicio.obtener_orden_para_documento(consecutivo_ot)

    # Generar el PDF (en memoria, nunca se escribe a disco: ver nota de
    # seguridad en OrdenTrabajoPDFGenerator.generar_pdf)
    try:
        pdf_generator = OrdenTrabajoPDFGenerator()
        nombre_archivo = f"orden_trabajo_{consecutivo_ot}.pdf"
        pdf_bytes = pdf_generator.generar_pdf(orden)

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                # inline (no attachment): igual que la factura, para que se
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


@router.get("/{consecutivo_ot}/generar-factura")
async def generar_factura_orden_trabajo(consecutivo_ot: int):
    """Genera un PDF de factura en formato POS (ticket de 80mm)"""
    servicio = OrdenTrabajoServicio()

    # Generar la factura (toda la lógica de negocio está en el servicio,
    # en memoria: ver nota de seguridad en OrdenTrabajoPDFGenerator.generar_pdf)
    try:
        pdf_bytes = await servicio.generar_factura_pos(consecutivo_ot)
        nombre_archivo = f"factura_{consecutivo_ot}.pdf"

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
        logger.exception("Error generando factura de la orden %s", consecutivo_ot)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al generar la factura"
        )


@router.get("/{consecutivo_ot}", response_model=OrdenTrabajoResponseContract)
async def obtener_orden_trabajo(consecutivo_ot: int):
    """Obtiene una orden de trabajo completa con todos sus detalles"""
    servicio = OrdenTrabajoServicio()
    return await servicio.obtener_orden_por_id(consecutivo_ot)


@router.post("", response_model=OrdenTrabajoResponseContract, status_code=status.HTTP_201_CREATED)
async def crear_orden_trabajo(
    orden: OrdenTrabajoCreateContract,
    # user=Depends(AuthRequest(permissions=["ordenes:crear"]))
):
    """Crea una nueva orden de trabajo con sus productos/servicios"""
    servicio = OrdenTrabajoServicio()
    # Por ahora usa el recepcionista especificado en el contrato
    documento_usuario = orden.documento_usu_rp_ot
    return await servicio.crear_orden_trabajo(orden, documento_usuario)


@router.put("/{consecutivo_ot}", response_model=OrdenTrabajoResponseContract)
async def actualizar_orden_trabajo(
    consecutivo_ot: int,
    orden: OrdenTrabajoUpdateContract
):
    """Actualiza una orden de trabajo existente"""
    servicio = OrdenTrabajoServicio()
    return await servicio.actualizar_orden(consecutivo_ot, orden)


@router.patch("/{consecutivo_ot}/estado", response_model=OrdenTrabajoResponseContract)
async def cambiar_estado_orden(
    consecutivo_ot: int,
    estado: CambiarEstadoContract
):
    """Cambia el estado de una orden de trabajo"""
    servicio = OrdenTrabajoServicio()
    return await servicio.cambiar_estado(consecutivo_ot, estado)


@router.patch("/{consecutivo_ot}/entregar", response_model=OrdenTrabajoResponseContract)
async def entregar_orden_trabajo(
    consecutivo_ot: int,
    entrega: EntregarOrdenContract
):
    """Marca una orden de trabajo como entregada"""
    servicio = OrdenTrabajoServicio()
    return await servicio.entregar_orden(consecutivo_ot, entrega)


@router.post("/{consecutivo_ot}/productos", response_model=OrdenTrabajoResponseContract)
async def agregar_producto_a_orden(
    consecutivo_ot: int,
    detalle: DetalleOrdenTrabajoContract,
    # user=Depends(AuthRequest(permissions=["ordenes:modificar"]))
):
    """Agrega un producto/servicio a una orden de trabajo existente"""
    servicio = OrdenTrabajoServicio()

    # Obtener la orden para usar el documento del recepcionista
    orden = await servicio.obtener_orden_por_id(consecutivo_ot)
    documento_usuario = orden.documento_recepcionista

    return await servicio.agregar_producto(consecutivo_ot, detalle, documento_usuario)


@router.patch("/{consecutivo_ot}/productos/{cod_pro}", response_model=OrdenTrabajoResponseContract)
async def actualizar_cantidad_producto(
    consecutivo_ot: int,
    cod_pro: int,
    detalle: DetalleOrdenUpdateContract
):
    """
    Actualiza la cantidad de un producto en una orden de trabajo.
    Maneja automáticamente el ajuste de stock.
    """
    servicio = OrdenTrabajoServicio()
    return await servicio.actualizar_cantidad_producto(consecutivo_ot, cod_pro, detalle)


@router.delete("/{consecutivo_ot}/productos/{cod_pro}", response_model=OrdenTrabajoResponseContract)
async def eliminar_producto_de_orden(
    consecutivo_ot: int,
    cod_pro: int
):
    """Elimina un producto/servicio de una orden de trabajo"""
    servicio = OrdenTrabajoServicio()
    return await servicio.eliminar_producto(consecutivo_ot, cod_pro)
