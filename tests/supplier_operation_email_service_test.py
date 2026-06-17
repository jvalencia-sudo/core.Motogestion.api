import uuid
from unittest.mock import AsyncMock

import pytest

from domain.models.supplier.supplier_operation_email_model import (
    SupplierOperationEmailModel,
    VwSupplierOperationEmailModel,
)
from domain.services.supplier.supplier_operation_email_service import (
    SupplierOperationEmailService,
)
from repository.supplier.supplier_operation_email_repository import (
    SupplierOperationEmailRepository,
)


class TestSupplierOperationEmailService:
    @pytest.fixture
    def service(self) -> SupplierOperationEmailService:
        return SupplierOperationEmailService()

    @pytest.fixture
    def repository(self) -> SupplierOperationEmailRepository:
        return SupplierOperationEmailRepository()

    async def test_bulk_create_should_call_repository_execute_values(
        self, service, repository
    ):
        # Arrange
        repository.execute_values = AsyncMock()
        service.repository = repository

        models = [
            SupplierOperationEmailModel(supplier_operation_id=10, email_id=100),
            SupplierOperationEmailModel(supplier_operation_id=20, email_id=200),
        ]

        # Act
        await service.bulk_create(models)

        # Assert
        repository.execute_values.assert_called_once_with(models)

    async def test_get_suppliers_notified_should_return_vw(self, service, repository):
        # Arrange
        operation_id = 10
        mock_supplier = [
            {
                "operation_id": operation_id,
                "supplier_id": 100,
                "is_primary": True,
                "key": uuid.uuid4(),
                "email": "poli@gmail.com",
                "email_id": 1,
                "supplier_name": "Proveedor",
            }
        ]

        repository.get_suppliers_notified = AsyncMock(return_value=mock_supplier)
        service.repository = repository
        # Act
        result = await service.get_suppliers_notified(operation_id)
        # Assert
        service.repository.get_suppliers_notified.assert_awaited_once_with(operation_id)
        assert isinstance(result, list)
        assert isinstance(result[0], VwSupplierOperationEmailModel)

    async def test_get_notified_suppliers_by_operation_supplier_should_return_vw(
        self, service, repository
    ):
        # Arrange
        operation_id = 10
        supplier_id = 100
        mock_supplier = [
            {
                "operation_id": operation_id,
                "supplier_id": supplier_id,
                "is_primary": True,
                "key": uuid.uuid4(),
                "email": "poli@gmail.com",
                "email_id": 1,
                "supplier_name": "Proveedor",
            }
        ]

        repository.get_notified_suppliers_by_operation_supplier = AsyncMock(
            return_value=mock_supplier
        )
        service.repository = repository
        # Act
        result = await service.get_notified_suppliers_by_operation_supplier(
            operation_id, supplier_id
        )
        # Assert
        service.repository.get_notified_suppliers_by_operation_supplier.assert_awaited_once_with(
            operation_id, supplier_id
        )
        assert isinstance(result, list)
        assert isinstance(result[0], VwSupplierOperationEmailModel)

    async def test_get_notified_email_by_operation_supplier_should_return_emails(
        self, service, repository
    ):
        # Arrange
        operation_id = 1
        supplier_id = 42

        mock_data = [
            VwSupplierOperationEmailModel(
                operation_id=operation_id,
                supplier_id=supplier_id,
                is_primary=True,
                key=uuid.uuid4(),
                email="correo1@x.com",
                email_id=101,
                supplier_name="Proveedor A",
            ),
            VwSupplierOperationEmailModel(
                operation_id=operation_id,
                supplier_id=supplier_id,
                is_primary=False,
                key=uuid.uuid4(),
                email="correo2@x.com",
                email_id=102,
                supplier_name="Proveedor A",
            ),
        ]

        service.get_notified_suppliers_by_operation_supplier = AsyncMock(
            return_value=mock_data
        )

        # Act
        result = await service.get_notified_email_by_operation_supplier(
            operation_id, supplier_id
        )

        # Assert
        service.get_notified_suppliers_by_operation_supplier.assert_awaited_once_with(
            operation_id, supplier_id
        )
        assert result == ["correo1@x.com", "correo2@x.com"]
        assert len(result) == 2

    async def test_get_notified_email_by_operation_should_return_emails(
        self, service, repository
    ):
        # Arrange
        operation_id = 123

        mock_data = [
            VwSupplierOperationEmailModel(
                operation_id=operation_id,
                supplier_id=1,
                is_primary=True,
                key=uuid.uuid4(),
                email="notificado1@x.com",
                email_id=100,
                supplier_name="Proveedor 1",
            ),
            VwSupplierOperationEmailModel(
                operation_id=operation_id,
                supplier_id=2,
                is_primary=False,
                key=uuid.uuid4(),
                email="notificado2@x.com",
                email_id=101,
                supplier_name="Proveedor 2",
            ),
        ]

        service.get_suppliers_notified = AsyncMock(return_value=mock_data)

        # Act
        result = await service.get_notified_email_by_operation(operation_id)

        # Assert
        service.get_suppliers_notified.assert_awaited_once_with(operation_id)
        assert result == ["notificado1@x.com", "notificado2@x.com"]
        assert len(result) == 2
