from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from domain.models.auth.user_model import UserPermissionsModel, UserWithBusinessesModel
from domain.models.configuration.process_field import ProcessFieldModel
from domain.models.configuration.step_model import StepModel
from domain.models.core.business_model import BusinessModel
from domain.models.orders.order_model import OrderModel, VwOrderModel
from domain.services.orders.order_service import OrderService
from infrastructure.commons.enums.order_state import OrderStateEnum
from infrastructure.commons.enums.user import UserTypeEnum
from infrastructure.exceptions.domain_exception import DomainException
from repository.auth.user_business_repository import UserBusinessRepository
from repository.auth.user_repository import UserRepository
from repository.orders.order_repository import OrderRepository


class TestOrderService:
    @pytest.fixture
    def service(self) -> OrderService:
        return OrderService()

    @pytest.fixture
    def repository(self) -> OrderRepository:
        return OrderRepository()

    @pytest.fixture
    def user_repository(self) -> UserRepository:
        return UserRepository()

    @pytest.fixture
    def user_business_repository(self) -> UserBusinessRepository:
        return UserBusinessRepository()

    async def test_get_all_should_return_all_orders(self, service, repository):
        # Arrange
        repository.get_all = AsyncMock(
            return_value=[
                {
                    "order_id": 1,
                    "order_code": "",
                    "customer_id": 1,
                    "order_state_id": 1,
                    "created_at": datetime.now(),
                    "business_id": 1,
                    "process_id": None,
                    "description": None,
                }
            ]
        )
        service.repository = repository

        # Act
        orders = await service.get_all()

        # Assert
        assert len(orders) == 1
        assert isinstance(orders[0], OrderModel)
        repository.get_all.assert_called_once()

    async def test_get_vw_all_should_return_filtered_orders(
        self,
        service: OrderService,
        repository: OrderRepository,
        user_repository: UserRepository,
        user_business_repository: UserBusinessRepository,
    ):
        # Arrange
        mock_user = UserWithBusinessesModel(
            user_id=1,
            customer_id=100,
            user_name="TEST",
            email="test@test.com",
            sub_id_usu="000001",
            user_type=UserTypeEnum.ADMIN,
            businesses=[
                BusinessModel(
                    business_id=1,
                    business_name="Business 1",
                    code="BUS-001",
                )
            ],
        )
        mock_session = UserPermissionsModel(user_id="000001", permissions=[])
        mock_order = [
            {
                "order_id": 1,
                "order_code": "ORD-001",
                "customer_id": 100,
                "customer_name": "TEST",
                "email": "test@test.com",
                "customer_code": "CUS-001",
                "process_name": "PROCESS",
                "order_state_name": "STATE",
                "process_id": 1000,
                "order_state_id": 1,
                "description": "DESCRIPTION",
                "created_at": datetime.now(),
                "business_id": 10000,
            }
        ]
        repository.get_vw_all = AsyncMock(return_value=mock_order)

        user_repository.get_user_by_sub = AsyncMock(return_value=mock_user)
        user_business_repository.get_vw_all = AsyncMock(return_value=[])

        service.repository = repository
        service.user_service.repository = user_repository
        service.user_service.user_business_repository = user_business_repository

        service.user_service.get_auth_user_by_sub = AsyncMock(return_value=mock_user)
        # Act
        orders = await service.get_vw_all(mock_session)

        # Assert
        assert len(orders) == 1
        assert isinstance(orders[0], VwOrderModel)

    async def test_get_by_code_should_return_order(
        self,
        service: OrderService,
        repository: OrderRepository,
        user_repository: UserRepository,
        user_business_repository: UserBusinessRepository,
    ):
        # Arrange
        mock_user = UserWithBusinessesModel(
            user_id=1,
            customer_id=100,
            user_name="TEST",
            email="test@test.com",
            sub_id_usu="000001",
            user_type=UserTypeEnum.ADMIN,
            businesses=[
                BusinessModel(
                    business_id=1,
                    business_name="Business 1",
                    code="BUS-001",
                )
            ],
        )

        mock_order = {
            "order_id": 1,
            "order_code": "ORD-001",
            "customer_id": 100,
            "customer_name": "TEST",
            "email": "test@test.com",
            "customer_code": "CUS-001",
            "process_name": "PROCESS",
            "order_state_name": "STATE",
            "process_id": 1000,
            "order_state_id": 1,
            "description": "DESCRIPTION",
            "created_at": datetime.now(),
            "business_id": 10000,
        }
        repository.get_by_code = AsyncMock(return_value=mock_order)

        user_repository.get_user_by_sub = AsyncMock(return_value=mock_user)
        user_business_repository.get_vw_all = AsyncMock(return_value=[])

        service.repository = repository
        service.user_service.repository = user_repository
        service.user_service.user_business_repository = user_business_repository

        service.user_service.get_auth_user_by_sub = AsyncMock(return_value=mock_user)

        # Act
        order = await service.get_by_code(
            "ORD-001", UserPermissionsModel(user_id="000001", permissions=[])
        )

        # Assert
        assert isinstance(order, VwOrderModel)
        assert order.order_id == 1
        repository.get_by_code.assert_called_once_with("ORD-001")

    async def test_update_order_process_should_create_steps_and_fields(
        self, service: OrderService, repository: OrderRepository
    ):
        # Arrange
        mock_steps = [
            StepModel.model_validate(
                {
                    "step_id": 1,
                    "step_name": "Step 1",
                    "process_id": 1,
                    "step_order": 1,
                    "details": None,
                    "created_at": datetime.now(),
                    "visible_to_customer": True,
                }
            ),
            StepModel.model_validate(
                {
                    "step_id": 2,
                    "step_name": "Step 2",
                    "process_id": 1,
                    "step_order": 2,
                    "details": None,
                    "created_at": datetime.now(),
                    "visible_to_customer": True,
                }
            ),
        ]

        mock_fields = [
            ProcessFieldModel.model_validate(
                {
                    "process_field_id": 1,
                    "process_id": 1,
                    "field_name": "Field 1",
                    "created_at": datetime.now(),
                }
            ),
            ProcessFieldModel.model_validate(
                {
                    "process_field_id": 2,
                    "process_id": 1,
                    "field_name": "Field 2",
                    "created_at": datetime.now(),
                }
            ),
        ]

        service.repository = repository
        service.step_service.get_by_process = AsyncMock(return_value=mock_steps)
        service.process_field_service.get_by_process = AsyncMock(
            return_value=mock_fields
        )
        service.order_step_service.create = AsyncMock()
        service.order_field_service.create = AsyncMock()
        repository.update_order_process = AsyncMock()

        # Act
        await service.update_order_process(1, 100)

        # Assert
        repository.update_order_process.assert_called_once_with(
            1, 100, OrderStateEnum.InProgress
        )
        assert service.order_step_service.create.call_count == 2
        assert service.order_field_service.create.call_count == 2

    async def test_update_order_process_should_raise_exception_when_no_steps(
        self, service: OrderService, repository: OrderRepository
    ):
        # Arrange
        service.repository = repository
        service.step_service.get_by_process = AsyncMock(return_value=[])
        service.process_field_service.get_by_process = AsyncMock(return_value=[])

        # Act & Assert
        with pytest.raises(DomainException, match="The process has no steps"):
            await service.update_order_process(1, 100)
