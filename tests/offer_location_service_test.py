from unittest.mock import AsyncMock
import pytest

from domain.models.core.offer_location_model import OfferLocationModel
from domain.services.core.offer_location_service import OfferLocationService


from repository.base_repository import BaseRepository


class TestOfferLocationService:
    @pytest.fixture
    def service(self) -> OfferLocationService:
        return OfferLocationService()

    @pytest.fixture
    def repository(self) -> BaseRepository:
        return BaseRepository("core", "offer_location", "offer_location_id")

    async def test_bulk_create_should_call_repository_execute_values(
        self, service, repository
    ):
        # Arrange
        repository.execute_values = AsyncMock()
        service.repository = repository

        models = [
            OfferLocationModel(offer_id=10, location_id=100, tariff=3.4),
            OfferLocationModel(offer_id=20, location_id=200, tariff=4.0),
        ]

        # Act
        await service.bulk_create(models)

        # Assert
        repository.execute_values.assert_called_once_with(models)
