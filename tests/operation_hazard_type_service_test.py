from unittest.mock import AsyncMock
import pytest

from domain.models.core.operation_hazard_type_model import OperationHazardTypeModel
from domain.services.operation.operation_hazard_type_service import (
    OperationHazardTypeService,
)

from repository.base_repository import BaseRepository


class TestOperationHazardTypeService:
    @pytest.fixture
    def service(self) -> OperationHazardTypeService:
        return OperationHazardTypeService()

    @pytest.fixture
    def repository(self) -> BaseRepository:
        return BaseRepository(
            "operation", "operation_hazard_type", "operation_hazard_type_id"
        )

    async def test_bulk_create_should_call_repository_execute_values(
        self, service, repository
    ):
        # Arrange
        repository.execute_values = AsyncMock()
        service.repository = repository

        models = [
            OperationHazardTypeModel(operation_id=10, hazard_type_id=100),
            OperationHazardTypeModel(operation_id=20, hazard_type_id=200),
        ]

        # Act
        await service.bulk_create(models)

        # Assert
        repository.execute_values.assert_called_once_with(models)
