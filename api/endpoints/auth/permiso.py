from typing import List

from fastapi import APIRouter, Response
from starlette.status import HTTP_204_NO_CONTENT


from domain.models.auth.permiso_modelo import PermisoModelo, VwPermisoModelo

from domain.services.auth.permiso_servicio import PermisoServicio

router = APIRouter()


@router.get("", response_model=List[PermisoModelo])
async def get():
    return await PermisoServicio().get_all()

@router.get("/", response_model=List[VwPermisoModelo])
async def obtener_vw_permiso():
    return await PermisoServicio().obtener_vw_permisos()
@router.post("", response_model=PermisoModelo)
async def create(client: PermisoModelo):
    await PermisoServicio().create(client)
    return Response(
        status_code=201,
    )


@router.delete("/{rol_id}", status_code=HTTP_204_NO_CONTENT)
async def delete(rol_id: int):
    return await PermisoServicio().delete(rol_id)


@router.get("/{rol_id}", response_model=PermisoModelo)
async def get_customer_by_id(rol_id: int):
    return await PermisoServicio().get_by_id(rol_id)


