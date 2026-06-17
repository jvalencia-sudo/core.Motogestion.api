from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from domain.contracts.supplier.supplier_operation_contract import SupplierEmailsContract
from domain.models.supplier.supplier_operation_email_model import (
    VwSupplierOperationEmailModel,
)
from domain.models.supplier.supplier_operation_model import SupplierOperationModel
from domain.services.supplier.supplier_operation_service import SupplierOperationService
from repository.supplier.supplier_operation import SupplierOperationRepository


class TestSupplierOperationService:
    @pytest.fixture
    def service(self) -> SupplierOperationService:
        return SupplierOperationService()

    @pytest.fixture
    def repository(self) -> SupplierOperationRepository:
        return SupplierOperationRepository()

    @pytest.mark.asyncio
    async def test_get_notified_suppliers_by_operation_should_return_grouped_contracts(
        self, service: SupplierOperationService, repository: SupplierOperationRepository
    ):
        # Arrange
        operation_id = 42

        mock_data = [
            VwSupplierOperationEmailModel(
                operation_id=operation_id,
                supplier_id=1,
                is_primary=True,
                key=uuid4(),
                email="uno@x.com",
                email_id=100,
                supplier_name="Proveedor Uno",
            ),
            VwSupplierOperationEmailModel(
                operation_id=operation_id,
                supplier_id=1,
                is_primary=False,
                key=uuid4(),
                email="dos@x.com",
                email_id=101,
                supplier_name="Proveedor Uno",
            ),
            VwSupplierOperationEmailModel(
                operation_id=operation_id,
                supplier_id=2,
                is_primary=True,
                key=uuid4(),
                email="otro@x.com",
                email_id=200,
                supplier_name="Proveedor Dos",
            ),
        ]

        service.supplier_operation_email_service.get_suppliers_notified = AsyncMock(
            return_value=mock_data
        )
        # Act
        result = await service.get_notified_suppliers_by_operation(operation_id)

        # Assert
        service.supplier_operation_email_service.get_suppliers_notified.assert_awaited_once_with(
            operation_id
        )
        assert len(result) == 2
        assert isinstance(result[0], SupplierEmailsContract)

    async def test_get_operation_by_key_should_return_expected_model(
        self, service, repository
    ):
        # Arrange
        key = uuid4()
        expected_data = {
            "supplier_operation_id": 1,
            "operation_id": 100,
            "supplier_id": 200,
            "key": key,
        }

        repository.get_operation_by_key = AsyncMock(return_value=expected_data)
        service.repository = repository

        # Act
        result = await service.get_operation_by_key(key)

        # Assert
        repository.get_operation_by_key.assert_awaited_once_with(key)
        assert isinstance(result, SupplierOperationModel)
        assert result.key == key

    async def test_get_operation_supplier_should_return_model(
        self, service, repository
    ):
        # Arrange
        operation_id = 1
        supplier_id = 2
        key = uuid4()
        expected_data = {
            "supplier_operation_id": 123,
            "operation_id": operation_id,
            "supplier_id": supplier_id,
            "key": key,
        }

        repository.get_supplier_operation = AsyncMock(return_value=expected_data)
        service.repository = repository

        # Act
        result = await service.get_operation_supplier(operation_id, supplier_id)

        # Assert
        repository.get_supplier_operation.assert_awaited_once_with(
            operation_id, supplier_id
        )
        assert isinstance(result, SupplierOperationModel)
        assert result.operation_id == operation_id
