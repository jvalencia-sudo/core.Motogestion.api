import uuid
from unittest.mock import AsyncMock, Mock
import pytest

from domain.contracts.operation.operation_detail_contract import (
    TotalWeightContract,
    GroupedByDestinationContract,
    GroupedUnitsContract,
)
from domain.models.operation.operation_detail_model import (
    OperationDetailModel,
    VwOperationDetailUnitModel,
)
from domain.models.supplier.supplier_operation_model import SupplierOperationModel
from domain.services.operation.operation_detail_service import OperationDetailService
from repository.base_repository import BaseRepository
from repository.operation.operation_detail_repository import OperationDetailRepository


class TestOperationDetailService:
    @pytest.fixture
    def service(self) -> OperationDetailService:
        return OperationDetailService()

    @pytest.fixture
    def repository(self) -> BaseRepository:
        return OperationDetailRepository()

    async def test_bulk_create_should_call_repository_execute_values(
        self, service, repository
    ):
        # Arrange
        repository.execute_values = AsyncMock()
        service.repository = repository

        models = [
            OperationDetailModel(
                operation_id=10,
                unit_type_id=1,
                location_id=100,
                unit_count=5,
                unit_weight=2.5,
                net_weight=12.5,
                gross_weight=15.0,
                height=1.2,
                width=0.8,
                length=2.0,
            ),
            OperationDetailModel(
                operation_id=20,
                unit_type_id=2,
                location_id=200,
                unit_count=10,
                unit_weight=3.0,
                net_weight=30.0,
                gross_weight=35.0,
                height=1.5,
                width=1.0,
                length=2.5,
            ),
        ]

        # Act
        await service.bulk_create(models)

        # Assert
        repository.execute_values.assert_called_once_with(models)

    async def test_get_grouped_operation_details_by_key(
        self, service: OperationDetailService, repository: OperationDetailRepository
    ):
        # Arrange
        key = uuid.uuid4()
        operation_id = 1

        supplier_operation_mock = SupplierOperationModel(
            supplier_operation_id=1,
            operation_id=1,
            supplier_id=45,
            key=key,
        )

        mock_operation_detail = [
            VwOperationDetailUnitModel(
                operation_detail_id=1,
                unit_type_name="Container",
                operation_id=operation_id,
                location_id=1,
                destination="Destination A",
                unit_weight=100,
                gross_weight=150,
                net_weight=120,
                height=2.5,
                width=2.5,
                length=6.0,
                unit_count=4,
            ),
            VwOperationDetailUnitModel(
                operation_detail_id=2,
                unit_type_name="Container",
                operation_id=operation_id,
                location_id=1,
                destination="Destination B",
                unit_weight=200,
                gross_weight=250,
                net_weight=220,
                height=2.5,
                width=2.5,
                length=6.0,
                unit_count=10,
            ),
        ]
        expected_grouped_units = GroupedUnitsContract(
            grouped_by_destination=[
                GroupedByDestinationContract(
                    destination="Destination A",
                    details=[mock_operation_detail[0]],
                    total_weight=TotalWeightContract(
                        total_net_weight=120, total_gross_weight=150
                    ),
                ),
                GroupedByDestinationContract(
                    destination="Destination B",
                    details=[mock_operation_detail[1]],
                    total_weight=TotalWeightContract(
                        total_net_weight=220, total_gross_weight=250
                    ),
                ),
            ],
            total_weight_global=TotalWeightContract(
                total_net_weight=340, total_gross_weight=400
            ),
        )

        service.supplier_operation_service.get_operation_by_key = AsyncMock(
            return_value=supplier_operation_mock
        )
        service.get_detail_of_operation_by_operation_id = AsyncMock(
            return_value=mock_operation_detail
        )
        service.group_by_destination = Mock(return_value=expected_grouped_units)

        # Act
        result = await service.get_grouped_operation_details_by_key(key)

        # Assert
        service.supplier_operation_service.get_operation_by_key.assert_called_once_with(
            key
        )
        service.get_detail_of_operation_by_operation_id.assert_called_once_with(
            operation_id
        )
        service.group_by_destination.assert_called_once_with(mock_operation_detail)

        assert isinstance(
            result.grouped_by_destination[0], GroupedByDestinationContract
        )

    async def test_get_grouped_operation_details_by_operation_id(
        self, service: OperationDetailService, repository: OperationDetailRepository
    ):
        # Arrange
        operation_id = 1
        mock_operation_detail = [
            VwOperationDetailUnitModel(
                operation_detail_id=1,
                unit_type_name="Container",
                operation_id=operation_id,
                location_id=1,
                destination="Destination A",
                unit_weight=100,
                gross_weight=150,
                net_weight=120,
                height=2.5,
                width=2.5,
                length=6.0,
                unit_count=4,
            ),
            VwOperationDetailUnitModel(
                operation_detail_id=2,
                unit_type_name="Container",
                operation_id=operation_id,
                location_id=1,
                destination="Destination B",
                unit_weight=200,
                gross_weight=250,
                net_weight=220,
                height=2.5,
                width=2.5,
                length=6.0,
                unit_count=10,
            ),
        ]
        expected_grouped_units = GroupedUnitsContract(
            grouped_by_destination=[
                GroupedByDestinationContract(
                    destination="Destination A",
                    details=[mock_operation_detail[0]],
                    total_weight=TotalWeightContract(
                        total_net_weight=120, total_gross_weight=150
                    ),
                ),
                GroupedByDestinationContract(
                    destination="Destination B",
                    details=[mock_operation_detail[1]],
                    total_weight=TotalWeightContract(
                        total_net_weight=220, total_gross_weight=250
                    ),
                ),
            ],
            total_weight_global=TotalWeightContract(
                total_net_weight=340, total_gross_weight=400
            ),
        )

        service.get_detail_of_operation_by_operation_id = AsyncMock(
            return_value=mock_operation_detail
        )
        service.group_by_destination = Mock(return_value=expected_grouped_units)

        # Act
        result = await service.get_grouped_operation_details_by_operation_id(
            operation_id
        )

        # Assert
        service.get_detail_of_operation_by_operation_id.assert_called_once_with(
            operation_id
        )
        service.group_by_destination.assert_called_once_with(mock_operation_detail)

        assert isinstance(
            result.grouped_by_destination[0], GroupedByDestinationContract
        )

    async def test_get_detail_of_operation_by_operation_id_returns_parsed_models(
        self, service: OperationDetailService, repository: OperationDetailRepository
    ):
        # Arrange
        operation_id = 123
        mock_data = [
            {
                "operation_detail_id": 1,
                "unit_type_name": "Container",
                "operation_id": 123,
                "location_id": 1,
                "destination": "A",
                "unit_count": 10,
                "unit_weight": 100,
                "net_weight": 90,
                "gross_weight": 110,
                "height": 2.5,
                "width": 2.5,
                "length": 6.0,
            }
        ]
        repository.get_vw_operation_detail_by_operation_id = AsyncMock(
            return_value=mock_data
        )
        service.repository = repository
        # Act
        result = await service.get_detail_of_operation_by_operation_id(operation_id)

        # Assert
        assert len(result) == 1
        assert isinstance(result[0], VwOperationDetailUnitModel)
        assert result[0].destination == "A"

    def test_group_details_by_destination_groups_correctly(
        self, service: OperationDetailService, repository: OperationDetailRepository
    ):
        # Arrange
        detail_1 = VwOperationDetailUnitModel(
            operation_detail_id=1,
            unit_type_name="Container",
            operation_id=123,
            location_id=1,
            destination="A",
            unit_count=1,
            unit_weight=100,
            net_weight=90,
            gross_weight=110,
            height=2.5,
            width=2.5,
            length=6.0,
            address=None,
        )

        detail_2 = VwOperationDetailUnitModel(
            operation_detail_id=2,
            unit_type_name="Container",
            operation_id=123,
            location_id=2,
            destination="B",
            unit_count=2,
            unit_weight=200,
            net_weight=180,
            gross_weight=220,
            height=2.5,
            width=2.5,
            length=6.0,
            address=None,
        )

        detail_3 = VwOperationDetailUnitModel(
            operation_detail_id=3,
            unit_type_name="Container",
            operation_id=123,
            location_id=3,
            destination="A",
            unit_count=3,
            unit_weight=300,
            net_weight=270,
            gross_weight=330,
            height=2.5,
            width=2.5,
            length=6.0,
            address=None,
        )

        operation_details = [detail_1, detail_2, detail_3]

        # Act
        result = OperationDetailService.group_details_by_destination(operation_details)

        # Assert
        assert isinstance(result, dict)
        assert set(result.keys()) == {"A", "B"}
        assert len(result["A"]) == 2
        assert len(result["B"]) == 1
        assert result["A"][0].operation_detail_id == 1
        assert result["A"][1].operation_detail_id == 3
        assert result["B"][0].operation_detail_id == 2

    def test_calculate_totals_by_destination_returns_correct_totals(self):
        # Arrange
        grouped = {
            "A": [
                VwOperationDetailUnitModel(
                    operation_detail_id=1,
                    unit_type_name="Container",
                    operation_id=1,
                    location_id=1,
                    destination="A",
                    unit_count=2,
                    unit_weight=100,
                    net_weight=80,
                    gross_weight=100,
                    height=2.5,
                    width=2.5,
                    length=6.0,
                ),
                VwOperationDetailUnitModel(
                    operation_detail_id=2,
                    unit_type_name="Container",
                    operation_id=1,
                    location_id=1,
                    destination="A",
                    unit_count=2,
                    unit_weight=150,
                    net_weight=120,
                    gross_weight=160,
                    height=2.5,
                    width=2.5,
                    length=6.0,
                ),
            ],
            "B": [
                VwOperationDetailUnitModel(
                    operation_detail_id=3,
                    unit_type_name="Container",
                    operation_id=1,
                    location_id=1,
                    destination="B",
                    unit_count=1,
                    unit_weight=200,
                    net_weight=180,
                    gross_weight=190,
                    height=2.5,
                    width=2.5,
                    length=6.0,
                )
            ],
        }

        # Act
        result = OperationDetailService.calculate_totals_by_destination(grouped)

        # Assert
        assert result["A"] == TotalWeightContract(
            total_net_weight=200, total_gross_weight=260
        )
        assert result["B"] == TotalWeightContract(
            total_net_weight=180, total_gross_weight=190
        )

    def test_calculate_total_global_returns_correct_total(
        self, service: OperationDetailService
    ):
        # Arrange
        details = [
            VwOperationDetailUnitModel(
                operation_detail_id=1,
                unit_type_name="Container",
                operation_id=1,
                location_id=1,
                destination="A",
                unit_count=1,
                unit_weight=100,
                net_weight=100,
                gross_weight=110,
                height=2.5,
                width=2.5,
                length=6.0,
            ),
            VwOperationDetailUnitModel(
                operation_detail_id=2,
                unit_type_name="Container",
                operation_id=1,
                location_id=1,
                destination="B",
                unit_count=1,
                unit_weight=150,
                net_weight=150,
                gross_weight=170,
                height=2.5,
                width=2.5,
                length=6.0,
            ),
        ]

        # Act
        result = service.calculate_total_global(details)

        # Assert
        assert result == TotalWeightContract(
            total_net_weight=250, total_gross_weight=280
        )

    def test_group_by_destination_returns_correct_contract(
        self, service: OperationDetailService
    ):
        # Arrange

        operation_details = [
            VwOperationDetailUnitModel(
                operation_detail_id=1,
                unit_type_name="Container",
                operation_id=1,
                location_id=10,
                destination="A",
                unit_count=2,
                unit_weight=100,
                net_weight=80,
                gross_weight=100,
                height=2.5,
                width=2.5,
                length=6.0,
            ),
            VwOperationDetailUnitModel(
                operation_detail_id=2,
                unit_type_name="Container",
                operation_id=1,
                location_id=10,
                destination="A",
                unit_count=2,
                unit_weight=150,
                net_weight=120,
                gross_weight=160,
                height=2.5,
                width=2.5,
                length=6.0,
            ),
            VwOperationDetailUnitModel(
                operation_detail_id=3,
                unit_type_name="Container",
                operation_id=1,
                location_id=11,
                destination="B",
                unit_count=1,
                unit_weight=200,
                net_weight=180,
                gross_weight=190,
                height=2.5,
                width=2.5,
                length=6.0,
            ),
        ]

        # Act
        result = service.group_by_destination(operation_details)

        # Assert
        assert isinstance(result, GroupedUnitsContract)
        assert len(result.grouped_by_destination) == 2
