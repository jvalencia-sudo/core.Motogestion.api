from typing import Dict, List, NoReturn

from domain.models.orders.order_field import OrderFieldModel, VwOrderFieldModel
from domain.services.base_service import BaseService
from infrastructure.exceptions.domain_exception import DomainException
from infrastructure.utils.date import get_current_colombian_time
from repository.orders.order_field_repository import OrderFieldRepository


class OrderFieldService(BaseService[OrderFieldModel, OrderFieldRepository]):
    def __init__(self):
        super().__init__(OrderFieldRepository())

    def __parse__(self, record: Dict) -> OrderFieldModel:
        return OrderFieldModel.model_validate(record)

    async def get_by_order(self, order_id: int) -> List[VwOrderFieldModel]:
        records = await self.repository.get_by_order(order_id)
        return self.__parse_all_custom__(records, VwOrderFieldModel)

    async def update_value(self, order_field_id: int, value: str) -> NoReturn:
        order_field = await self.get_by_id(order_field_id)
        if order_field:
            order_field.field_value = value
            order_field.updated_at = get_current_colombian_time()
            await self.update(order_field)
        else:
            raise DomainException("Order field not found")
