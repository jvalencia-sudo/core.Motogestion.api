from typing import List
from fastapi import APIRouter, status

from domain.contracts.motos.marca_contract import (
    MarcaCreateContract,
    MarcaUpdateContract,
    MarcaResponseContract
)
from domain.services.marcas.marca_servicio import MarcaServicio

router = APIRouter()


@router.get("", response_model=List[MarcaResponseContract])
async def obtener_marcas():
    """
    Obtiene todas las marcas.
    """
    servicio = MarcaServicio()
    return await servicio.obtener_todas_marcas()


@router.get("/resumen", response_model=List)
async def obtener_marcas_resumen():
    """
    Obtiene todas las marcas con el total de motos registradas.
    """
    servicio = MarcaServicio()
    return await servicio.obtener_marcas_con_resumen()



@router.get("/{cod_mar}", response_model=MarcaResponseContract)
async def obtener_marca(cod_mar: int):
    """
    Obtiene una marca específica por su código.

    - **cod_mar**: Código de la marca
    """
    servicio = MarcaServicio()
    return await servicio.obtener_marca_por_id(cod_mar)


@router.post("", response_model=MarcaResponseContract, status_code=status.HTTP_201_CREATED)
async def crear_marca(marca: MarcaCreateContract):
    """
    Crea una nueva marca.

    - **nombre_mar**: Nombre de la marca (requerido, máx 50 caracteres)
    """
    servicio = MarcaServicio()
    return await servicio.crear_marca(marca)


@router.put("/{cod_mar}", response_model=MarcaResponseContract)
async def actualizar_marca(cod_mar: int, marca: MarcaUpdateContract):
    """
    Actualiza una marca existente.

    - **cod_mar**: Código de la marca a actualizar
    - **nombre_mar**: Nuevo nombre de la marca (opcional)
    """
    servicio = MarcaServicio()
    return await servicio.actualizar_marca(cod_mar, marca)
