from typing import Dict

from domain.models.core.vehicle_type_model import VehicleTypeModel
from domain.services.base_service import BaseService
from repository.base_repository import BaseRepository


class VehicleTypeService(BaseService[VehicleTypeModel, None]):
    def __init__(self):
        super().__init__(BaseRepository("core", "vehicle_type", "vehicle_type_id"))

    def __parse__(self, record: Dict) -> VehicleTypeModel:
        return VehicleTypeModel.model_validate(record)
