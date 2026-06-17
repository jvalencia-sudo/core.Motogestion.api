from unittest.mock import AsyncMock

import pytest

from domain.contracts.supplier.supplier_contract import (
    SupplierWithEmailsContract,
    EmailContract,
    SupplierEditContract,
    EmailUpsertContract,
    SupplierCreateContract,
)
from domain.models.supplier.email_model import EmailModel
from domain.models.supplier.supplier_model import SupplierModel
from domain.services.supplier.supplier_service import SupplierService
from repository.supplier.supplier_repository import SupplierRepository


class TestSupplierService:
    @pytest.fixture
    def service(self) -> SupplierService:
        return SupplierService()

    @pytest.fixture
    def repository(self) -> SupplierRepository:
        return SupplierRepository()

    def test_map_supplier_with_emails_should_return_contract(
        self, service: SupplierService
    ):
        mock_supplier = [
            SupplierModel(supplier_id=1, supplier_name="mock name", status=True)
        ]
        mock_email = [
            EmailModel(
                email_id=1,
                email="proveedor@gmail.com",
                supplier_id=1,
                is_primary=True,
                status=True,
            )
        ]

        result = service.map_suppliers_with_emails(mock_supplier, mock_email)
        print(result)
        assert len(result) == 1
        assert isinstance(result[0], SupplierWithEmailsContract)
        assert isinstance(result[0].emails[0], EmailContract)

    async def test_get_suppliers_with_emails_should_return_expected_result(
        self, service: SupplierService
    ):
        # Arrange
        mock_suppliers = [
            SupplierModel(supplier_id=1, supplier_name="Proveedor A", status=True)
        ]
        mock_emails = [
            EmailModel(
                email_id=10,
                email="proveedor@correo.com",
                supplier_id=1,
                is_primary=True,
                status=True,
            )
        ]
        expected_result = [
            SupplierWithEmailsContract(
                supplier_id=1,
                supplier_name="Proveedor A",
                status=True,
                emails=[
                    EmailContract(
                        email_id=10, email="proveedor@correo.com", is_primary=True
                    )
                ],
            )
        ]
        service.get_all = AsyncMock(return_value=mock_suppliers)
        service.email_service.get_all = AsyncMock(return_value=mock_emails)

        result = await service.get_suppliers_with_emails()

        assert result == expected_result
        assert len(result) == 1
        assert isinstance(result[0], SupplierWithEmailsContract)

    async def test_get_suppliers_with_email_by_status_should_return_expected_result(
        self, service: SupplierService, repository: SupplierRepository
    ):
        # Arrange
        mock_suppliers = [
            {
                "supplier_id": 1,
                "supplier_name": "Proveedor A",
                "status": True,
            }
        ]
        mock_emails = [
            EmailModel(
                email_id=10,
                email="proveedor@correo.com",
                supplier_id=1,
                is_primary=True,
                status=True,
            ),
        ]
        expected_result = [
            SupplierWithEmailsContract(
                supplier_id=1,
                supplier_name="Proveedor A",
                status=True,
                emails=[
                    EmailContract(
                        email_id=10, email="proveedor@correo.com", is_primary=True
                    )
                ],
            )
        ]
        repository.get_suppliers_by_status = AsyncMock(return_value=mock_suppliers)
        service.repository = repository
        service.email_service.get_emails_by_status = AsyncMock(return_value=mock_emails)

        # Act

        result = await service.get_suppliers_with_email_by_status(True)

        # Assert
        assert result == expected_result
        assert len(result) == 1
        assert isinstance(result[0], SupplierWithEmailsContract)

    async def test_get_supplier_with_emails_by_id_should_return_expected_contract(
        self, service: SupplierService
    ):
        # Arrange
        supplier_id = 1
        mock_supplier = SupplierModel(
            supplier_id=supplier_id,
            supplier_name="Proveedor X",
            status=True,
        )
        mock_emails = [
            EmailModel(
                email_id=100,
                email="contacto@proveedor.com",
                supplier_id=supplier_id,
                is_primary=True,
                status=True,
            ),
            EmailModel(
                email_id=101,
                email="soporte@proveedor.com",
                supplier_id=supplier_id,
                is_primary=False,
                status=False,
            ),
        ]

        service.get_by_id = AsyncMock(return_value=mock_supplier)
        service.email_service.get_email_by_supplier = AsyncMock(
            return_value=mock_emails
        )

        # Act
        result = await service.get_supplier_with_emails_by_id(supplier_id)

        # Assert
        assert isinstance(result, SupplierEditContract)
        assert len(result.emails) == 2
        assert all(isinstance(email, EmailUpsertContract) for email in result.emails)

    async def test_create_supplier_should_create_supplier_and_emails(
        self, service: SupplierService, repository: SupplierRepository
    ):
        # Arrange

        repository.create = AsyncMock(return_value=1)
        service.email_service.bulk_create = AsyncMock()
        service.repository = repository
        data_supplier = SupplierCreateContract(
            supplier_name="Proveedor X",
            emails=[
                EmailUpsertContract(email="test1@x.com", is_primary=True, status=True),
                EmailUpsertContract(email="test2@x.com", is_primary=False, status=True),
            ],
        )

        # Act
        await service.create_supplier(data_supplier)

        # Assert
        service.email_service.bulk_create.assert_awaited_once()
        assert service.email_service.bulk_create.call_count == 1

    async def test_edit_supplier_should_update_supplier_and_emails(
        self, service: SupplierService, repository: SupplierRepository
    ):
        # Arrange
        supplier_id = 1
        existing_emails = [
            EmailModel(
                email_id=10,
                email="old1@x.com",
                supplier_id=supplier_id,
                is_primary=True,
                status=True,
            ),
            EmailModel(
                email_id=11,
                email="old2@x.com",
                supplier_id=supplier_id,
                is_primary=False,
                status=True,
            ),
        ]

        # Mock de emails existentes
        service.email_service.get_email_by_supplier = AsyncMock(
            return_value=existing_emails
        )

        # Nuevos datos del proveedor
        supplier_edit = SupplierEditContract(
            supplier_id=supplier_id,
            supplier_name="Nuevo nombre",
            status=True,
            emails=[
                EmailUpsertContract(
                    email_id=10, email="old1@x.com", is_primary=True, status=True
                ),
                EmailUpsertContract(
                    email_id=0, email="new@x.com", is_primary=False, status=True
                ),
            ],
        )
        repository.update = AsyncMock()
        service.repository = repository
        service.email_service.bulk_create = AsyncMock()
        service.email_service.update = AsyncMock()
        # Act
        await service.edit_supplier(supplier_edit)

        # Assert

        service.email_service.bulk_create.assert_awaited_once()
        service.email_service.update.assert_awaited()

        new_email = service.email_service.bulk_create.call_args[0][0][0]
        assert new_email.email == "new@x.com"
        assert new_email.email_id == 0
        assert new_email.supplier_id == supplier_id

        updated_emails = [
            call[0][0] for call in service.email_service.update.call_args_list
        ]
        updated_ids = [e.email_id for e in updated_emails]
        assert 10 in updated_ids

        assert any(e.email_id == 11 and e.status is False for e in updated_emails)

    async def test_disable_supplier_should_call_update_status_with_false(
        self, service, repository
    ):
        # Arrange
        supplier_id = 42
        repository.update_status_supplier = AsyncMock()
        service.repository = repository
        # Act
        await service.disable_supplier(supplier_id)

        # Assert
        service.repository.update_status_supplier.assert_awaited_once_with(
            supplier_id, False
        )

    async def test_enable_supplier_should_call_update_status_with_true(
        self, service, repository
    ):
        # Arrange
        supplier_id = 77
        repository.update_status_supplier = AsyncMock()
        service.repository = repository
        # Act
        await service.enable_supplier(supplier_id)

        # Assert
        service.repository.update_status_supplier.assert_awaited_once_with(
            supplier_id, True
        )
