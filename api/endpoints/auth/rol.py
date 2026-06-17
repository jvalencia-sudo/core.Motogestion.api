from typing import List, Optional

from fastapi import APIRouter, Response
from starlette.status import HTTP_204_NO_CONTENT

from domain.models.auth.rol_modelo import RolModelo


from domain.services.auth.rol_servicio import RolServicio


router = APIRouter()


@router.get("", response_model=List[RolModelo])
async def get():
    return await RolServicio().get_all()


@router.post("", response_model=RolModelo)
async def create(client: RolModelo):
    await RolServicio().create(client)
    return Response(
        status_code=201,
    )


@router.delete("/{rol_id}", status_code=HTTP_204_NO_CONTENT)
async def delete(rol_id: int):
    return await RolServicio().delete(rol_id)


@router.get("/{rol_id}", response_model=RolModelo)
async def get_customer_by_id(rol_id: int):
    return await RolServicio().get_by_id(rol_id)

@router.put(
    "",
    status_code=HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def update(
    rol: RolModelo,
):
    await RolServicio().update(rol)
