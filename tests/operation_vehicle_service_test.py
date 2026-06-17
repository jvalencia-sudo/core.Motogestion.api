from unittest.mock import AsyncMock
import pytest

from domain.models.operation.operation_vehicle_type_model import (
    OperationVehicleTypeModel,
)
from domain.services.operation.operation_vehicle_type_service import (
    OperationVehicleTypeService,
)
from repository.base_repository import BaseRepository


class TestOperationVehicleTypeService:
    @pytest.fixture
    def service(self) -> OperationVehicleTypeService:
        return OperationVehicleTypeService()

    @pytest.fixture
    def repository(self) -> BaseRepository:
        return BaseRepository(
            "operation", "operation_vehicle_type", "operation_vehicle_type_id"
        )

    async def test_bulk_create_should_call_repository_execute_values(
        self, service, repository
    ):
        # Arrange
        repository.execute_values = AsyncMock()
        service.repository = repository

        models = [
            OperationVehicleTypeModel(
                operation_vehicle_type_id=1, operation_id=10, vehicle_type_id=100
            ),
            OperationVehicleTypeModel(
                operation_vehicle_type_id=2, operation_id=20, vehicle_type_id=200
            ),
        ]

        # Act
        await service.bulk_create(models)

        # Assert
        repository.execute_values.assert_called_once_with(models)
