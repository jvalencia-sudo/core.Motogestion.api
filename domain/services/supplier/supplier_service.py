from typing import List, Dict

from domain.contracts.supplier.supplier_contract import (
    SupplierWithEmailsContract,
    EmailContract,
    SupplierCreateContract,
    SupplierEditContract,
    EmailUpsertContract,
)
from domain.models.supplier.email_model import EmailModel
from domain.models.supplier.supplier_model import SupplierModel
from domain.services.base_service import BaseService
from domain.services.supplier.email_service import EmailService
from infrastructure.exceptions.domain_exception import DomainException
from repository.supplier.supplier_repository import SupplierRepository


class SupplierService(BaseService[SupplierModel, SupplierRepository]):
    def __init__(self):
        super().__init__(SupplierRepository())
        self.email_service = EmailService()

    def __parse__(self, record: Dict) -> SupplierModel:
        return SupplierModel.model_validate(record)

    @staticmethod
    def map_suppliers_with_emails(
        suppliers: List[SupplierModel],
        emails: List[EmailModel],
    ) -> List[SupplierWithEmailsContract]:
        suppliers_dict: Dict[int, SupplierWithEmailsContract] = {
            supplier.supplier_id: SupplierWithEmailsContract(
                supplier_id=supplier.supplier_id,
                supplier_name=supplier.supplier_name,
                emails=[],
                status=supplier.status,
            )
            for supplier in suppliers
        }

        for email in emails:
            supplier_id = email.supplier_id
            if supplier_id in suppliers_dict:
                suppliers_dict[supplier_id].emails.append(
                    EmailContract(
                        email_id=email.email_id,
                        email=email.email,
                        is_primary=email.is_primary,
                    )
                )

        return list(suppliers_dict.values())

    async def get_suppliers_with_emails(self) -> List[SupplierWithEmailsContract]:
        suppliers = await self.get_all()
        emails = await self.email_service.get_all()
        return self.map_suppliers_with_emails(suppliers, emails)

    async def get_suppliers_with_email_by_status(
        self, status: bool
    ) -> List[SupplierWithEmailsContract]:
        suppliers_data = await self.repository.get_suppliers_by_status(status)
        suppliers = self.__parse_all_custom__(suppliers_data, SupplierModel)
        emails = await self.email_service.get_emails_by_status(status)
        return self.map_suppliers_with_emails(suppliers, emails)

    async def get_supplier_with_emails_by_id(self, supplier_id) -> SupplierEditContract:
        supplier = await self.get_by_id(supplier_id)
        emails_results = await self.email_service.get_email_by_supplier(supplier_id)
        emails = [EmailUpsertContract.model_validate(email) for email in emails_results]
        supplier_with_emails = SupplierEditContract(
            supplier_id=supplier.supplier_id,
            supplier_name=supplier.supplier_name,
            emails=emails,
            status=supplier.status,
        )

        return supplier_with_emails

    async def create_supplier(self, data_supplier: SupplierCreateContract):
        supplier = SupplierModel(supplier_name=data_supplier.supplier_name, status=True)
        supplier_id = await self.repository.create(supplier)
        emails = []
        for email in data_supplier.emails:
            emails.append(
                EmailModel(
                    email=email.email,
                    supplier_id=supplier_id,
                    is_primary=email.is_primary,
                    status=email.status,
                )
            )
        if emails:
            await self.email_service.bulk_create(emails)

    async def edit_supplier(self, supplier: SupplierEditContract):
        emails_results = await self.email_service.get_email_by_supplier(
            supplier.supplier_id
        )
        updated_supplier = SupplierModel(
            supplier_id=supplier.supplier_id,
            supplier_name=supplier.supplier_name,
            status=supplier.status,
        )
        await self.repository.update(updated_supplier)

        existing_emails = {email.email_id: email for email in emails_results}
        new_emails = []
        emails_to_update = []
        primary_email_set = False

        for email in supplier.emails:
            if email.is_primary:
                if primary_email_set:
                    raise DomainException("Only one email can be marked as primary.")
                primary_email_set = True

            email_model = EmailModel(
                email_id=email.email_id,
                email=email.email,
                supplier_id=supplier.supplier_id,
                is_primary=email.is_primary,
                status=email.status,
            )

            if email.email_id in existing_emails:
                emails_to_update.append(email_model)
            else:
                new_emails.append(email_model)

        existing_email_ids = set(existing_emails.keys())
        incoming_email_ids = {
            email.email_id for email in supplier.emails if email.email_id
        }
        emails_to_disable = [
            EmailModel(
                email_id=email_id,
                email=existing_emails[email_id].email,
                supplier_id=supplier.supplier_id,
                is_primary=existing_emails[email_id].is_primary,
                status=False,
            )
            for email_id in existing_email_ids - incoming_email_ids
        ]

        if new_emails:
            await self.email_service.bulk_create(new_emails)
        if emails_to_update:
            for email in emails_to_update:
                await self.email_service.update(email)
        if emails_to_disable:
            for email in emails_to_disable:
                await self.email_service.update(email)

    async def disable_supplier(self, supplier_id: int):
        await self.repository.update_status_supplier(supplier_id, False)

    async def enable_supplier(self, supplier_id: int):
        await self.repository.update_status_supplier(supplier_id, True)
