from unittest.mock import AsyncMock

import pytest

from domain.models.supplier.email_model import EmailModel
from domain.services.supplier.email_service import EmailService
from repository.supplier.email_repository import EmailRepository


class TestEmailService:
    @pytest.fixture
    def service(self) -> EmailService:
        return EmailService()

    @pytest.fixture
    def repository(self) -> EmailRepository:
        return EmailRepository()

    async def test_get_email_by_supplier_should_return_parsed_models(
        self, service, repository
    ):
        supplier_id = 123
        mock_emails = [
            {
                "email_id": 1,
                "email": "test@x.com",
                "supplier_id": supplier_id,
                "is_primary": True,
                "status": True,
            },
        ]
        repository.get_by_supplier = AsyncMock(return_value=mock_emails)
        service.repository = repository
        result = await service.get_email_by_supplier(supplier_id)

        service.repository.get_by_supplier.assert_awaited_once_with(supplier_id)
        assert isinstance(result, list)
        assert isinstance(result[0], EmailModel)
        assert result[0].email == "test@x.com"

    async def test_get_emails_by_status_should_return_parsed_models(
        self, service, repository
    ):
        mock_emails = [
            {
                "email_id": 2,
                "email": "active@x.com",
                "supplier_id": 1,
                "is_primary": False,
                "status": True,
            }
        ]
        repository.get_emails_by_status = AsyncMock(return_value=mock_emails)
        service.repository = repository
        result = await service.get_emails_by_status(True)

        service.repository.get_emails_by_status.assert_awaited_once_with(True)
        assert isinstance(result, list)
        assert isinstance(result[0], EmailModel)
        assert result[0].status is True

    async def test_bulk_create_should_delegate_to_repository(self, service, repository):
        repository.execute_values = AsyncMock()
        service.repository = repository
        emails = [
            EmailModel(
                email_id=0,
                email="bulk@x.com",
                supplier_id=1,
                is_primary=False,
                status=True,
            )
        ]

        await service.bulk_create(emails)

        repository.execute_values.assert_awaited_once_with(emails)
