import uuid
from typing import Dict, List, Optional

from domain.contracts.supplier.supplier_contract import EmailContract
from domain.contracts.supplier.supplier_operation_contract import (
    SupplierEmailsContract,
)

from domain.models.supplier.supplier_operation_model import SupplierOperationModel
from domain.services.base_service import BaseService
from domain.services.supplier.email_service import EmailService
from domain.services.supplier.supplier_operation_email_service import (
    SupplierOperationEmailService,
)

from repository.supplier.supplier_operation import SupplierOperationRepository


class SupplierOperationService(
    BaseService[SupplierOperationModel, SupplierOperationRepository]
):
    def __init__(self):
        super().__init__(SupplierOperationRepository())
        self.email_service = EmailService()
        self.supplier_operation_email_service = SupplierOperationEmailService()

    def __parse__(self, record: Dict) -> SupplierOperationModel:
        return SupplierOperationModel.model_validate(record)

    async def get_notified_suppliers_by_operation(
        self, operation_id: int
    ) -> List[SupplierEmailsContract]:
        data_supplier = (
            await self.supplier_operation_email_service.get_suppliers_notified(
                operation_id
            )
        )
        supplier_dict = {}

        for item in data_supplier:
            supplier_id = item.supplier_id

            if supplier_id not in supplier_dict:
                supplier_dict[supplier_id] = {
                    "key": item.key,
                    "supplier_name": item.supplier_name,
                    "emails": [],
                }

            supplier_dict[supplier_id]["emails"].append(
                EmailContract(
                    email_id=item.email_id, email=item.email, is_primary=item.is_primary
                )
            )

        result = [
            SupplierEmailsContract(
                supplier_id=supplier_id,
                supplier_name=data["supplier_name"],
                key=data["key"],
                emails=data["emails"],
            )
            for supplier_id, data in supplier_dict.items()
        ]

        return result

    async def get_operation_by_key(self, key: uuid.UUID) -> SupplierOperationModel:
        supplier_operation = await self.repository.get_operation_by_key(key)
        return self.__parse__(supplier_operation)

    async def get_operation_supplier(
        self, operation_id: int, supplier_id: int
    ) -> Optional[SupplierOperationModel]:
        supplier_operation = await self.repository.get_supplier_operation(
            operation_id, supplier_id
        )
        if supplier_operation is None:
            return None  #
        return self.__parse__(supplier_operation)
