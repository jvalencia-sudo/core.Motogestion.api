from typing import List
from fastapi import APIRouter, status, HTTPException, Depends
from domain.contracts.ordenes_trabajo.reclamo_contract import (
    ReclamoCreateContract,
    ReclamoUpdateContract,
    ReclamoResponseContract,
    ReclamoResumenContract
)
from domain.services.ordenes_trabajo.reclamo_servicio import ReclamoServicio
from infrastructure.exceptions.domain_exception import DomainException

router = APIRouter(
    prefix="/reclamos",
    tags=["Reclamos"]
)


@router.get("", response_model=List[ReclamoResumenContract])
async def obtener_reclamos():
    """Obtiene todos los reclamos con información resumida"""
    servicio = ReclamoServicio()
    return await servicio.obtener_todos_reclamos()


# Rutas específicas ANTES de la ruta parametrizada
@router.get("/orden/{consecutivo_ot}", response_model=List[ReclamoResumenContract])
async def obtener_reclamos_por_orden(consecutivo_ot: int):
    """Obtiene todos los reclamos asociados a una orden de trabajo"""
    servicio = ReclamoServicio()
    try:
        return await servicio.obtener_reclamos_por_orden(consecutivo_ot)
    except DomainException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.get("/cliente/{documento_cli}", response_model=List[ReclamoResumenContract])
async def obtener_reclamos_por_cliente(documento_cli: str):
    """Obtiene todos los reclamos de un cliente específico"""
    servicio = ReclamoServicio()
    return await servicio.obtener_reclamos_por_cliente(documento_cli)


@router.get("/moto/{placa_mot}", response_model=List[ReclamoResumenContract])
async def obtener_reclamos_por_moto(placa_mot: str):
    """Obtiene todos los reclamos de una moto específica"""
    servicio = ReclamoServicio()
    return await servicio.obtener_reclamos_por_moto(placa_mot)


@router.get("/garantia/{estado_garantia}", response_model=List[ReclamoResumenContract])
async def obtener_reclamos_por_garantia(estado_garantia: str):
    """Obtiene reclamos filtrados por estado de garantía (VIGENTE, VENCIDA, SIN INFORMACIÓN)"""
    servicio = ReclamoServicio()
    try:
        return await servicio.obtener_reclamos_por_estado_garantia(estado_garantia)
    except DomainException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


# Ruta parametrizada genérica AL FINAL
@router.get("/{cod_rec}", response_model=ReclamoResponseContract)
async def obtener_reclamo(cod_rec: int):
    """Obtiene un reclamo completo con todos sus detalles"""
    servicio = ReclamoServicio()
    try:
        return await servicio.obtener_reclamo_por_id(cod_rec)
    except DomainException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post("", response_model=ReclamoResponseContract, status_code=status.HTTP_201_CREATED)
async def crear_reclamo(reclamo: ReclamoCreateContract):
    """Crea un nuevo reclamo"""
    servicio = ReclamoServicio()
    try:
        return await servicio.crear_reclamo(reclamo)
    except DomainException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.put("/{cod_rec}", response_model=ReclamoResponseContract)
async def actualizar_reclamo(cod_rec: int, reclamo: ReclamoUpdateContract):
    """Actualiza un reclamo existente"""
    servicio = ReclamoServicio()
    try:
        return await servicio.actualizar_reclamo(cod_rec, reclamo)
    except DomainException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.delete("/{cod_rec}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_reclamo(cod_rec: int):
    """Elimina un reclamo"""
    servicio = ReclamoServicio()
    try:
        await servicio.eliminar_reclamo(cod_rec)
    except DomainException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
