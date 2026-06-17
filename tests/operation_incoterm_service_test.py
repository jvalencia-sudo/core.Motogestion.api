from unittest.mock import AsyncMock
import pytest

from domain.models.operation.operation_incoterm_model import OperationIncotermModel
from domain.services.operation.operation_incoterm_service import (
    OperationIncotermService,
)
from repository.base_repository import BaseRepository


class TestOperationIncotermService:
    @pytest.fixture
    def service(self) -> OperationIncotermService:
        return OperationIncotermService()

    @pytest.fixture
    def repository(self) -> BaseRepository:
        return BaseRepository(
            "operation", "operation_incoterm", "operation_incoterm_id"
        )

    async def test_bulk_create_should_call_repository_execute_values(
        self, service, repository
    ):
        # Arrange
        repository.execute_values = AsyncMock()
        service.repository = repository

        models = [
            OperationIncotermModel(operation_id=10, incoterm_id=100),
            OperationIncotermModel(operation_id=20, incoterm_id=200),
        ]

        # Act
        await service.bulk_create(models)

        # Assert
        repository.execute_values.assert_called_once_with(models)
