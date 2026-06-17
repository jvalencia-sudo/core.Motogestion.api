from typing import Dict, List

from domain.models.orders.document_history_model import DocumentHistoryModel
from domain.services.base_service import BaseService
from repository.orders.document_history_repository import DocumentHistoryRepository


class DocumentHistoryService(
    BaseService[DocumentHistoryModel, DocumentHistoryRepository]
):
    def __init__(self):
        super().__init__(DocumentHistoryRepository())

    def __parse__(self, record: Dict) -> DocumentHistoryModel:
        return DocumentHistoryModel.model_validate(record)

    async def get_history_by_document(
        self, document_id: int
    ) -> List[DocumentHistoryModel]:
        return self.__parse_all__(
            await self.repository.get_history_by_document(document_id)
        )
