from typing import Dict, List, NoReturn, Union
from datetime import datetime

from domain.models.auth.user_model import UserPermissionsModel
from domain.models.orders.order_field import OrderFieldModel
from domain.models.orders.order_model import OrderModel, VwOrderModel
from domain.models.orders.order_step import OrderStepModel
from domain.services.auth.user_service import UserService
from domain.services.base_service import BaseService
from domain.services.configuration.process_field_service import ProcessFieldService
from domain.services.configuration.step_service import StepService
from domain.services.orders.order_field_service import OrderFieldService
from domain.services.orders.order_step_service import OrderStepService
from domain.services.orders.order_product_service import OrderProductService
from infrastructure.commons.enums.order_state import OrderStateEnum
from infrastructure.commons.enums.step_state import StepStateEnum
from infrastructure.exceptions.domain_exception import DomainException
from infrastructure.utils.date import get_current_colombian_time
from repository.orders.order_repository import OrderRepository
from domain.models.orders.order_create_model import (
    OrderCreateModel,
)
from domain.models.orders.order_product_model import OrderProductModel


class OrderService(BaseService[OrderModel, OrderRepository]):
    def __init__(self):
        super().__init__(OrderRepository())
        self.step_service = StepService()
        self.order_step_service = OrderStepService()
        self.user_service = UserService()
        self.process_field_service = ProcessFieldService()
        self.order_field_service = OrderFieldService()
        self.order_product_service = OrderProductService()

    def __parse__(self, record: Dict) -> OrderModel:
        return OrderModel.model_validate(record)

    async def get_vw_all(self, session: UserPermissionsModel) -> List[VwOrderModel]:
        user = await self.user_service.get_auth_user_by_sub(session.user_id)
        businesses_ids = [b.business_id for b in user.businesses]
        if len(businesses_ids) == 0:
            return []
        records = await self.repository.get_vw_all(user.customer_id, businesses_ids)
        return self.__parse_all_custom__(records, VwOrderModel)

    async def get_by_code(
        self, code: str, session: UserPermissionsModel
    ) -> VwOrderModel:
        user = await self.user_service.get_auth_user_by_sub(session.user_id)
        order = await self.repository.get_by_code(code)
        user_business = [b.business_id for b in user.businesses]
        if (
            order.get("customer_id") != user.customer_id
            and order.get("business_id") not in user_business
        ):
            raise DomainException("You are not authorized to access this order")
        return VwOrderModel.model_validate(order)

    async def create_order(self, order: OrderModel) -> OrderModel:
        order.order_code = (await self.repository.generate_consecutive())["consecutive"]
        new_id = await self.repository.create(order)
        return await self.get_by_id(new_id)

    async def update_order_process(
        self, order_id: int, process_id: int
    ) -> Union[NoReturn, None]:
        steps = await self.step_service.get_by_process(process_id)
        fields = await self.process_field_service.get_by_process(process_id)
        if len(steps) > 0:
            await self.repository.update_order_process(
                order_id, process_id, OrderStateEnum.InProgress
            )
            for s in steps:
                await self.order_step_service.create(
                    OrderStepModel(
                        order_id=order_id,
                        step_id=s.step_id,
                        step_state_id=StepStateEnum.NotStarted,
                        complete=False,
                        notes=None,
                        updated_at=get_current_colombian_time(),
                    )
                )

            for f in fields:
                await self.order_field_service.create(
                    OrderFieldModel(
                        order_id=order_id,
                        process_field_id=f.process_field_id,
                        field_value=None,
                        updated_at=get_current_colombian_time(),
                    )
                )
        else:
            raise DomainException("The process has no steps")

    async def create_order_from_platform(
        self, order_data: OrderCreateModel
    ) -> OrderModel:
        # Create the order
        order = OrderModel(
            order_code=order_data.order_code,
            customer_id=order_data.customer_id,
            business_id=order_data.business_id,
            description=order_data.description,
            created_at=datetime.now(),
            order_state_id=1,  # Default to pending state
            process_id=None,
        )

        # Save the order
        new_order_id = await self.repository.create(order)
        created_order = await self.get_by_id(new_order_id)

        # Create order products
        for product in order_data.products:
            order_product = OrderProductModel(
                order_id=new_order_id,
                product_id=product.product_id,
                quantity=product.quantity,
                unit_of_measure=product.unit_of_measure,
            )
            await self.order_product_service.create(order_product)

        return created_order
