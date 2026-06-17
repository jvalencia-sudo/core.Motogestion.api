from typing import List, Dict

from repository.base_repository import BaseRepository


class DocumentHistoryRepository(BaseRepository):
    def __init__(self):
        super().__init__("orders", "document_history", "document_history_id")

    async def get_history_by_document(self, document_id: int) -> List[Dict]:
        return await self.execute(
            f"{self.build_select()} where document_id = %s", (document_id,)
        )
