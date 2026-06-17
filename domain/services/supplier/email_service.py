from typing import Dict, List

from domain.models.supplier.email_model import EmailModel
from domain.services.base_service import BaseService
from repository.supplier.email_repository import EmailRepository


class EmailService(BaseService[EmailModel, EmailRepository]):
    def __init__(self):
        super().__init__(EmailRepository())

    def __parse__(self, record: Dict) -> EmailModel:
        return EmailModel.model_validate(record)

    async def get_email_by_supplier(self, supplier_id: int) -> List[EmailModel]:
        results = await self.repository.get_by_supplier(supplier_id)
        emails = self.__parse_all_custom__(results, EmailModel)
        return emails

    async def get_emails_by_status(self, status: bool) -> List[EmailModel]:
        results = await self.repository.get_emails_by_status(status)
        emails = self.__parse_all_custom__(results, EmailModel)
        return emails

    async def bulk_create(self, models: List[EmailModel]) -> None:
        await self.repository.execute_values(models)
