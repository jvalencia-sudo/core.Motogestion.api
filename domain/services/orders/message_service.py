from typing import Dict, List

from domain.contracts.orders.message_contract import CreateMessageContract
from domain.models.auth.user_model import UserModel, UserPermissionsModel
from domain.models.orders.message_model import MessageModel, VwMessageModel
from domain.services.base_service import BaseService
from domain.services.auth.user_service import UserService
from infrastructure.utils.date import get_current_colombian_time
from repository.orders.message_repository import MessageRepository
from infrastructure.commons.enums.user import UserTypeEnum


class MessageService(BaseService[MessageModel, MessageRepository]):
    def __init__(self):
        super().__init__(MessageRepository())
        self.user_service = UserService()

    def __parse__(self, record: Dict) -> MessageModel:
        return MessageModel.model_validate(record)

    async def get_by_order(self, order_id: int) -> List[MessageModel]:
        return self.__parse_all__(await self.repository.get_by_order(order_id))

    async def get_recent_messages(
        self, sesion: UserPermissionsModel
    ) -> List[MessageModel]:
        user = await self.user_service.get_auth_user_by_sub(sesion.user_id)
        if user.user_type == UserTypeEnum.CUSTOMER and user.customer_id is None:
            return []
        return self.__parse_all_custom__(
            await self.repository.get_recent_messages(user.customer_id),
            VwMessageModel,
        )

    async def create_message(
        self,
        request: CreateMessageContract,
        user: UserModel,
    ):
        model = MessageModel(
            created_at=get_current_colombian_time(),
            message_content=request.message,
            order_id=request.order_id,
            title="",
            sender=user.user_name,
            sender_id=user.user_id,
        )
        await self.create(model)
