from typing import List, Optional

from fastapi import APIRouter, Response
from starlette.status import HTTP_204_NO_CONTENT

from domain.models.auth.vista_modelo import VistaModelo
from domain.services.auth.vista_servicio import VistaServicio

router = APIRouter()


@router.get("", response_model=List[VistaModelo])
async def get():
    return await VistaServicio().get_all()


@router.post("", response_model=VistaModelo)
async def create(client: VistaModelo):
    await VistaServicio().create(client)
    return Response(
        status_code=201,
    )


@router.delete("/{rol_id}", status_code=HTTP_204_NO_CONTENT)
async def delete(rol_id: int):
    return await VistaServicio().delete(rol_id)


@router.get("/{rol_id}", response_model=VistaModelo)
async def get_customer_by_id(rol_id: int):
    return await VistaServicio().get_by_id(rol_id)


