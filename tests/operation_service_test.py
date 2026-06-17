from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from domain.contracts.operation.operation_create_contract import (
    OperationCreateContract,
    LocationDetailContract,
    UnitDetailContract,
)
from domain.models.auth.user_model import UserModel, UserPermissionsModel
from domain.models.operation.operation_detail_model import VwOperationDetailModel
from domain.services.operation.operation_service import OperationService
from infrastructure.commons.constants.operation_code_prefix import OPERATION_CODE_PREFIX
from infrastructure.commons.enums.operation_status import OperationStatus
from infrastructure.commons.enums.user import UserTypeEnum
from repository.operation.operation_repository import OperationRepository
from domain.models.operation.operation_model import (
    VwOperationModel,
    OperationModel,
    VwOperationWithDetailModel,
)
from psycopg_pool import AsyncConnectionPool


class TestOperationService:
    @pytest.fixture
    async def override_db_pool(self):
        mock_pool = MagicMock(spec=AsyncConnectionPool)

        mock_conn = MagicMock()

        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=None)

        # AsyncGeneratorContextManager config
        transaction_mock = MagicMock()
        transaction_mock.__aenter__ = AsyncMock(return_value=mock_conn)
        transaction_mock.__aexit__ = AsyncMock(return_value=None)
        mock_conn.transaction = Mock(return_value=transaction_mock)

        mock_pool.connection = Mock(return_value=mock_conn)

        yield mock_pool

    @pytest.fixture
    def service(self) -> OperationService:
        return OperationService()

    @pytest.fixture
    def repository(self) -> OperationRepository:
        return OperationRepository()

    @pytest.mark.asyncio
    async def test_get_vw_operations_by_user(
        self,
        service: OperationService,
        repository: OperationRepository,
    ):
        # Arrange
        mock_user = UserModel(
            user_id=1,
            user_name="Mock name",
            email="user@gmail.com",
            sub_id_usu="000001",
            customer_id=1,
            user_type=UserTypeEnum.CUSTOMER,
        )
        mock_session = UserPermissionsModel(user_id="000001", permissions=[])

        repository.get_vw_operations_by_user = AsyncMock(
            return_value=[
                {
                    "operation_id": 1,
                    "operation_code": "OPR-1",
                    "user_id": 1,
                    "requires_escort": True,
                    "load_date": datetime.now(),
                    "created_at": datetime.now(),
                    "email": "user@gmail.com",
                    "observation": None,
                    "validity_date": datetime.now(),
                    "operation_type_name": "Mock operation",
                    "location_origin_name": "Mock location",
                    "service_type_name": "Mock service",
                    "operation_status_name": "Mock status",
                    "incoterms": ["Mock", "Mock"],
                    "offer_count": 2,
                    "operation_details": [
                        {
                            "unit_count": 1,
                            "unit_type": "Mock unit",
                            "location": "Mock location",
                            "unit_weight": 2.24,
                            "net_weight": 2.24,
                            "gross_weight": 2.24,
                            "height": 2.4,
                            "width": 2.24,
                            "length": 2.24,
                        }
                    ],
                }
            ]
        )
        service.repository = repository
        service.user_service.get_auth_user_by_sub = AsyncMock(return_value=mock_user)

        # Act
        operations = await service.get_vw_operations_by_user(mock_session)

        # Assert
        assert len(operations) == 1
        assert isinstance(operations[0], VwOperationModel)

    async def test_create_operation_success(
        self,
        override_db_pool,
        service: OperationService,
        repository: OperationRepository,
    ):
        # Arrange
        mock_user = UserModel(
            user_id=1,
            user_name="Mock name",
            email="user@gmail.com",
            sub_id_usu="000001",
            customer_id=1,
            user_type=UserTypeEnum.CUSTOMER,
        )
        mock_session = UserPermissionsModel(user_id="000001", permissions=[])
        mock_operation_data = OperationCreateContract(
            operation_type_id=1,
            location_origin_id=10,
            service_type_id=5,
            requires_escort=False,
            load_date=datetime.now(),
            observation="Test operation",
            validity_date=datetime.now(),
            hazard_type_ids=[2, 3],
            vehicle_type_ids=[1, 4],
            incoterm_ids=[7],
            locations=[
                LocationDetailContract(
                    location_id=1,
                    units=[
                        UnitDetailContract(
                            unit_type_id=1,
                            unit_count=10,
                            unit_weight=100,
                            net_weight=1000,
                            gross_weight=1100,
                            height=2.5,
                            width=2.0,
                            length=6.0,
                        ),
                    ],
                ),
            ],
        )

        service.repository = repository
        service.repository.pool = override_db_pool

        service.repository.create = AsyncMock(return_value=1)
        service.user_service.get_auth_user_by_sub = AsyncMock(return_value=mock_user)
        service.generate_next_operation_code = AsyncMock(return_value="OPR-1")
        service.operation_hazard_service = AsyncMock()
        service.operation_hazard_service.bulk_create = AsyncMock()

        service.operation_vehicle_service = AsyncMock()
        service.operation_vehicle_service.bulk_create = AsyncMock()

        service.operation_incoterm_service = AsyncMock()
        service.operation_incoterm_service.bulk_create = AsyncMock()

        service.operation_detail_service = AsyncMock()
        service.operation_detail_service.bulk_create = AsyncMock()

        # Act
        operation_id = await service.create_operation(mock_operation_data, mock_session)

        # Assert
        assert operation_id == 1
        service.repository.create.assert_called_once()
        service.operation_hazard_service.bulk_create.assert_called_once()
        service.operation_vehicle_service.bulk_create.assert_called_once()
        service.operation_incoterm_service.bulk_create.assert_called_once()
        service.operation_detail_service.bulk_create.assert_called_once()

    async def test_create_operation_hazard_service_error(
        self,
        override_db_pool,
        service: OperationService,
        repository: OperationRepository,
    ):
        # Arrange
        mock_user = UserModel(
            user_id=1,
            user_name="Mock name",
            email="user@gmail.com",
            sub_id_usu="000001",
            customer_id=1,
            user_type=UserTypeEnum.CUSTOMER,
        )
        mock_session = UserPermissionsModel(user_id="000001", permissions=[])
        mock_operation_data = OperationCreateContract(
            operation_type_id=1,
            location_origin_id=10,
            service_type_id=5,
            requires_escort=False,
            load_date=datetime.now(),
            observation="Test operation",
            validity_date=datetime.now(),
            hazard_type_ids=[2, 3],
            vehicle_type_ids=[1, 4],
            incoterm_ids=[7],
            locations=[
                LocationDetailContract(
                    location_id=1,
                    units=[
                        UnitDetailContract(
                            unit_type_id=1,
                            unit_count=10,
                            unit_weight=100,
                            net_weight=1000,
                            gross_weight=1100,
                            height=2.5,
                            width=2.0,
                            length=6.0,
                        ),
                    ],
                ),
            ],
        )

        service.repository = repository
        service.repository.pool = override_db_pool
        service.repository.create = AsyncMock(return_value=1)
        service.user_service.get_auth_user_by_sub = AsyncMock(return_value=mock_user)
        service.operation_hazard_service.bulk_create = AsyncMock(
            side_effect=Exception()
        )

        # Act & Assert
        with pytest.raises(Exception, match=""):  # Fix this after
            await service.create_operation(mock_operation_data, mock_session)

    async def test_generate_next_operation_code_should_return_code(
        self, service: OperationService
    ):
        # Arrange
        mock_results = [
            OperationModel(
                operation_id=1,
                operation_code=f"{OPERATION_CODE_PREFIX}-12",
                user_id=1,
                created_at=datetime.now(),
                requires_escort=False,
                validity_date=datetime.now(),
                load_date=datetime.now(),
                operation_type_id=1,
                location_origin_id=1,
                service_type_id=1,
                operation_status_id=1,
            )
        ]

        service.get_all = AsyncMock(return_value=mock_results)
        # Act
        code = await service.generate_next_operation_code()

        assert code == f"{OPERATION_CODE_PREFIX}-13"

    @pytest.mark.asyncio
    async def test_get_vw_operations_by_operation_id_should_return_vw_operation(
        self,
        service: OperationService,
        repository: OperationRepository,
    ):
        operation_id = 1
        repository.get_vw_operations_by_operation = AsyncMock(
            return_value={
                "operation_id": operation_id,
                "operation_code": "OPR-1",
                "user_id": 1,
                "requires_escort": True,
                "load_date": datetime.now(),
                "created_at": datetime.now(),
                "email": "user@gmail.com",
                "observation": None,
                "validity_date": datetime.now(),
                "operation_type_name": "Mock operation",
                "location_origin_name": "Mock location",
                "service_type_name": "Mock service",
                "operation_status_name": "Mock status",
                "incoterms": ["Mock", "Mock"],
                "offer_count": 2,
                "operation_details": [
                    {
                        "unit_count": 1,
                        "unit_type": "Mock unit",
                        "location": "Mock location",
                        "unit_weight": 2.24,
                        "net_weight": 2.24,
                        "gross_weight": 2.24,
                        "height": 2.4,
                        "width": 2.24,
                        "length": 2.24,
                    }
                ],
            }
        )
        service.repository = repository
        # Act
        operation = await service.get_vw_operation_by_operation_id(operation_id)

        # Assert

        assert isinstance(operation, VwOperationModel)
        assert len(operation.operation_details) == 1
        assert isinstance(operation.operation_details[0], VwOperationDetailModel)
        assert operation.operation_status_name == "Mock status"

    async def test_get_vw_operations_details_by_operation_id_should_return_vw_operation_with_detail(
        self,
        service: OperationService,
        repository: OperationRepository,
    ):
        operation_id = 1
        mock_operation_detail = {
            "operation_id": operation_id,
            "operation_code": "OPR-1",
            "user_id": 1,
            "requires_escort": True,
            "load_date": datetime.now(),
            "created_at": datetime.now(),
            "observation": "hello",
            "validity_date": datetime.now(),
            "operation_type_name": "Mock operation",
            "location_origin_name": "Mock location",
            "service_type_name": "Mock service",
            "operation_status_name": "Mock status",
            "offer_count": 2,
            "incoterms": ["Mock", "Mock"],
            "hazard_types": ["Mock", "Mock"],
            "vehicle_types": None,
            "is_local": False,
        }
        repository.get_vw_operations_details_by_operation_id = AsyncMock(
            return_value=mock_operation_detail
        )

        service.repository = repository

        operation = await service.get_vw_operations_details_by_operation_id(
            operation_id
        )

        assert isinstance(operation, VwOperationWithDetailModel)
        assert len(operation.incoterms) == 2

    async def test_update_status_operation_to_published_calls_repository(
        self,
        service: OperationService,
        repository: OperationRepository,
    ):
        # Arrange
        operation_id = 1
        repository.update_status_operation = AsyncMock()
        service.repository = repository
        operation_id = 42

        # Act
        await service.update_status_operation(operation_id, OperationStatus.Published)

        # Assert
        repository.update_status_operation.assert_awaited_once_with(
            operation_id,
            OperationStatus.Published,
        )
