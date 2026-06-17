import uuid
from unittest.mock import AsyncMock

import pytest

from domain.models.core.location_model import VwLocationModel
from domain.models.supplier.supplier_operation_model import SupplierOperationModel
from domain.services.core.location_service import LocationService
from repository.core.core_repository import LocationRepository


class TestLocationService:
    @pytest.fixture
    def service(self) -> LocationService:
        return LocationService()

    @pytest.fixture
    def repository(self) -> LocationRepository:
        return LocationRepository()

    async def test_get_location_of_operation_by_key_should_return_locations(
        self, service: LocationService, repository: LocationRepository
    ):
        # Arrange
        test_key = uuid.uuid4()

        mock_operation = SupplierOperationModel(
            supplier_operation_id=1,
            operation_id=123,
            supplier_id=45,
            key=test_key,
        )

        mock_locations = [
            {
                "location_id": 1,
                "location": "Warehouse A",
                "address": "123 Main St",
            },
            {
                "location_id": 2,
                "location": "Warehouse B",
                "address": "456 Secondary St",
            },
        ]

        service.supplier_operation.get_operation_by_key = AsyncMock(
            return_value=mock_operation
        )
        repository.get_vw_location_by_operation_id = AsyncMock(
            return_value=mock_locations
        )
        service.repository = repository

        # Act
        result = await service.get_location_of_operation_by_key(test_key)

        # Assert
        assert len(result) == 2
        assert isinstance(result[0], VwLocationModel)
        assert result[0].location == "Warehouse A"
        service.supplier_operation.get_operation_by_key.assert_called_once_with(
            test_key
        )
        repository.get_vw_location_by_operation_id.assert_called_once_with(123)
