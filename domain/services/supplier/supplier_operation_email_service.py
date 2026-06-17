from typing import Dict, List

from domain.models.supplier.supplier_operation_email_model import (
    SupplierOperationEmailModel,
    VwSupplierOperationEmailModel,
)
from domain.services.base_service import BaseService
from repository.supplier.supplier_operation_email_repository import (
    SupplierOperationEmailRepository,
)


class SupplierOperationEmailService(
    BaseService[SupplierOperationEmailModel, SupplierOperationEmailRepository]
):
    def __init__(self):
        super().__init__(SupplierOperationEmailRepository())

    def __parse__(self, record: Dict) -> SupplierOperationEmailModel:
        return SupplierOperationEmailModel.model_validate(record)

    async def bulk_create(self, models: List[SupplierOperationEmailModel]) -> None:
        await self.repository.execute_values(models)

    async def get_suppliers_notified(
        self, operation_id: int
    ) -> List[VwSupplierOperationEmailModel]:
        data_supplier = await self.repository.get_suppliers_notified(operation_id)
        return self.__parse_all_custom__(data_supplier, VwSupplierOperationEmailModel)

    async def get_notified_suppliers_by_operation_supplier(
        self, operation_id: int, supplier_id: int
    ) -> List[VwSupplierOperationEmailModel]:
        data_supplier = (
            await self.repository.get_notified_suppliers_by_operation_supplier(
                operation_id, supplier_id
            )
        )
        return self.__parse_all_custom__(data_supplier, VwSupplierOperationEmailModel)

    async def get_notified_email_by_operation_supplier(
        self, operation_id: int, supplier_id: int
    ) -> List[str]:
        data_supplier = await self.get_notified_suppliers_by_operation_supplier(
            operation_id, supplier_id
        )
        emails = [data.email for data in data_supplier]
        return emails

    async def get_notified_email_by_operation(self, operation_id: int) -> List[str]:
        data_supplier = await self.get_suppliers_notified(operation_id)
        emails = [data.email for data in data_supplier]
        return emails
