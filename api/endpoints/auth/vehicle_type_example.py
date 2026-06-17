from typing import List

from fastapi import APIRouter, Response
from starlette.status import HTTP_204_NO_CONTENT, HTTP_201_CREATED
from domain.models.core.vehicle_type_model import VehicleTypeModel
from domain.services.core.vehicle_type_service import VehicleTypeService

router = APIRouter()


@router.get("", response_model=List[VehicleTypeModel])
async def get():
    return await VehicleTypeService().get_all()


@router.post("", status_code=HTTP_201_CREATED)
async def create(vehicle_type: VehicleTypeModel):
    await VehicleTypeService().create(vehicle_type)


@router.delete(
    "/{vehicle_type_id}",
    status_code=HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete(vehicle_type_id: int):
    await VehicleTypeService().delete(vehicle_type_id)


@router.get("/{vehicle_type_id}", response_model=VehicleTypeModel)
async def get_vehicle_by_id(vehicle_type_id: int):
    return await VehicleTypeService().get_by_id(vehicle_type_id)


@router.put(
    "",
    status_code=HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def update(
    vehicle_type: VehicleTypeModel,
):
    await VehicleTypeService().update(vehicle_type)
