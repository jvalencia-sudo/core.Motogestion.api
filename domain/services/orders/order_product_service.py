from typing import Dict, List

from domain.models.orders.order_product_model import (
    OrderProductModel,
    VwOrderProductModel,
)
from domain.services.base_service import BaseService
from repository.orders.order_product_repository import OrderProductRepository


class OrderProductService(BaseService[OrderProductModel, OrderProductRepository]):
    def __init__(self):
        super().__init__(OrderProductRepository())

    def __parse__(self, record: Dict) -> OrderProductModel:
        return OrderProductModel.model_validate(record)

    async def get_by_order(self, order_id: int) -> List[VwOrderProductModel]:
        records = await self.repository.get_by_order(order_id)
        return self.__parse_all_custom__(records, VwOrderProductModel)
