from typing import Dict, List

from domain.models.orders.message_model import MessageModel
from domain.models.orders.order_model import VwOrderModel
from domain.models.orders.order_step import OrderStepModel, VwOrderStepModel
from domain.services.base_service import BaseService
from domain.services.configuration.step_service import StepService
from domain.services.configuration.step_state_service import StepStateService
from domain.services.core.business_service import BusinessService
from domain.services.core.customer_service import CustomerService
from domain.services.notification_service import NotificationService
from domain.services.orders.message_service import MessageService
from infrastructure.exceptions.domain_exception import DomainException
from infrastructure.utils.date import get_current_colombian_time
from repository.orders.order_repository import OrderRepository
from repository.orders.order_step_repository import OrderStepRepository
from domain.contracts.orders.message_contract import CreateMessageContract
from domain.models.auth.user_model import UserPermissionsModel
from domain.services.auth.user_service import UserService
from infrastructure.commons.enums.step_state import StepStateEnum
from infrastructure.commons.enums.order_state import OrderStateEnum


class OrderStepService(BaseService[OrderStepModel, OrderStepRepository]):
    def __init__(self):
        super().__init__(OrderStepRepository())
        self.message_service = MessageService()
        self.step_service = StepService()
        self.step_state_service = StepStateService()
        self.notification_service = NotificationService()
        self.order_repository = OrderRepository()
        self.customer_service = CustomerService()
        self.business_service = BusinessService()
        self.user_service = UserService()

    def __parse__(self, record: Dict) -> OrderStepModel:
        return OrderStepModel.model_validate(record)

    async def get_by_order(self, order_id: int) -> List[VwOrderStepModel]:
        records = await self.repository.get_by_order(order_id)
        return self.__parse_all_custom__(records, VwOrderStepModel)

    async def update_order_step(self, order_step_id: int, state_id: int, notes: str):
        order_step = await self.get_by_id(order_step_id)
        if not order_step:
            raise DomainException("The order step doesn't exist")
        if notes:
            order_step.notes = (
                f"{order_step.notes if order_step.notes else ''}{notes} \n"
            )
        order_step.step_state_id = state_id
        order_step.updated_at = get_current_colombian_time()
        order_step.complete = (
            True if state_id == StepStateEnum.Completed.value else False
        )
        await self.update(order_step)

        step = await self.step_service.get_by_id(order_step.step_id)
        state = await self.step_state_service.get_by_id(state_id)
        order = VwOrderModel.model_validate(
            await self.order_repository.get_by_id(order_step.order_id)
        )
        customer = await self.customer_service.get_by_id(order.customer_id)
        business = await self.business_service.get_by_id(order.business_id)

        all_steps = await self.get_by_order(order_step.order_id)
        all_steps_complete = all(
            step.step_state_id == StepStateEnum.Completed.value for step in all_steps
        )

        if all_steps_complete:
            await self.order_repository.update_order_process(
                order_id=order_step.order_id,
                process_id=order.process_id,
                order_state_id=OrderStateEnum.Complete.value,
            )

        await self.message_service.create(
            MessageModel(
                created_at=get_current_colombian_time(),
                order_id=order_step.order_id,
                title=f"The state of the step <strong>{step.step_name}</strong> has been updated to <strong>{state.step_state_name}</strong>",
                message_content=notes,
                sender="System",
                sender_id=None,
            )
        )

        await self.notification_service.send_order_status_email_notification(
            notes=notes,
            customer=customer,
            business=business,
            order=order,
            state=state,
            step=step,
            update_on=get_current_colombian_time(),
        )

    async def create_message(
        self, request: CreateMessageContract, session: UserPermissionsModel
    ) -> List[VwOrderStepModel]:
        user = await self.user_service.get_auth_user_by_sub(session.user_id)
        await self.message_service.create_message(request=request, user=user)
        order = VwOrderModel.model_validate(
            await self.order_repository.get_by_id(request.order_id)
        )
        customer = await self.customer_service.get_by_id(order.customer_id)
        business = await self.business_service.get_by_id(order.business_id)
        await self.notification_service.send_order_message_notification(
            message_content=request.message,
            message_from=user.user_name,
            customer=customer,
            business=business,
            order=order,
            posted_on=get_current_colombian_time(),
        )
        return await self.get_by_order(request.order_id)
