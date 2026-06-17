from typing import Dict

from domain.models.orders.order_state_model import OrderStateModel
from domain.services.base_service import BaseService
from repository.base_repository import BaseRepository


class OrderStateService(BaseService[OrderStateModel, None]):
    def __init__(self):
        super().__init__(BaseRepository("orders", "order_state", "order_state_id"))

    def __parse__(self, record: Dict) -> OrderStateModel:
        return OrderStateModel.model_validate(record)
