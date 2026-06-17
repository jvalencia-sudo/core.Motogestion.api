import pathlib
import uuid
from typing import List, NoReturn, Optional

from domain.contracts.orders.document_contract import (
    UploadDocumentContract,
    UploadDocumentVersionContract,
)
from domain.models.auth.user_model import UserPermissionsModel
from domain.models.orders.document_history_model import DocumentHistoryModel
from domain.models.orders.document_model import DocumentModel, VwDocumentModel
from domain.models.orders.message_model import MessageModel
from domain.models.orders.order_model import VwOrderModel
from domain.services.auth.user_service import UserService
from domain.services.base_service import BaseService
from domain.services.core.business_service import BusinessService
from domain.services.core.customer_service import CustomerService
from domain.services.notification_service import NotificationService
from domain.services.orders.document_history_service import DocumentHistoryService
from domain.services.orders.message_service import MessageService
from infrastructure.utils.date import get_current_colombian_time
from infrastructure.utils.s3 import upload_file
from repository.orders.document_repository import DocumentRepository
from repository.orders.order_repository import OrderRepository


class DocumentService(BaseService[DocumentModel, DocumentRepository]):
    def __init__(self):
        super().__init__(DocumentRepository())
        self.document_history_service = DocumentHistoryService()
        self.message_service = MessageService()
        self.notification_service = NotificationService()
        self.customer_service = CustomerService()
        self.business_service = BusinessService()
        self.order_repository = OrderRepository()
        self.user_service = UserService()

    def __parse__(self, record) -> DocumentModel:
        return DocumentModel.model_validate(record)

    async def get_by_order(self, order_id: int) -> List[VwDocumentModel]:
        records = await self.repository.get_by_order(order_id)
        return self.__parse_all_custom__(records, VwDocumentModel)

    async def upload_document(
        self, request: UploadDocumentContract, user_permissions: UserPermissionsModel
    ) -> NoReturn:
        documents = await self.get_by_order(request.order_id)
        existing_document: Optional[VwDocumentModel] = next(
            filter(lambda x: x.document_name == request.file.filename, documents), None
        )
        user = await self.user_service.get_auth_user_by_sub(user_permissions.user_id)

        file_name = await self.process_file(request)

        if existing_document:
            history = DocumentHistoryModel(
                document_key=existing_document.document_key,
                created_at=existing_document.created_at,
                document_id=existing_document.document_id,
                change_reason="",
                version_number=existing_document.current_version,
                change_timestamp=get_current_colombian_time(),
                changed_by=user.user_id,
            )
            await self.document_history_service.create(history)

            document = DocumentModel.model_validate(existing_document.model_dump())
            document.current_version += 1
            document.document_key = file_name

            await self.update(document)
            await self.message_service.create(
                MessageModel(
                    created_at=get_current_colombian_time(),
                    order_id=document.order_id,
                    title=f"The file <strong>{document.document_name}</strong> has been uploaded.",
                    message_content="Document version updated automatically.",
                    sender="System",
                    sender_id=None,
                )
            )

        else:
            document = DocumentModel(
                order_id=request.order_id,
                document_name=request.file.filename,
                document_key=file_name,
                created_at=get_current_colombian_time(),
                order_step_id=request.order_step_id,
            )

            document_id = await self.create(document)
            document_created = await self.get_by_id(document_id)
            await self.message_service.create(
                MessageModel(
                    created_at=get_current_colombian_time(),
                    order_id=document.order_id,
                    title=f"The file <strong>{document.document_name}</strong> has been uploaded.",
                    message_content="",
                    sender="System",
                    sender_id=None,
                )
            )

            order = VwOrderModel.model_validate(
                await self.order_repository.get_by_id(document.order_id)
            )
            customer = await self.customer_service.get_by_id(order.customer_id)
            business = await self.business_service.get_by_id(order.business_id)

            await self.document_history_service.create(
                DocumentHistoryModel(
                    document_key=document_created.document_key,
                    created_at=get_current_colombian_time(),
                    document_id=document_created.document_id,
                    change_reason="",
                    version_number=1,
                    change_timestamp=get_current_colombian_time(),
                    changed_by=user.user_id,
                )
            )

            await self.notification_service.send_new_file_uploaded_notification(
                file_name=document.document_name,
                notes="",
                customer=customer,
                business=business,
                order=order,
                uploaded_by=user.user_name,
                uploaded_on=get_current_colombian_time(),
            )

    @staticmethod
    async def process_file(request):
        with open(request.file.filename, "wb") as f:
            f.write(await request.file.read())
        extension = pathlib.Path(request.file.filename).suffix
        file_name = f"{uuid.uuid4()}{extension}"
        upload_file(request.file.filename, file_name, remove_on_upload=True)
        return file_name

    async def get_history(self, document_id: int) -> List[DocumentHistoryModel]:
        return await self.document_history_service.get_history_by_document(document_id)

    async def upload_document_version(
        self,
        request: UploadDocumentVersionContract,
        user_permissions: UserPermissionsModel,
    ):
        file_name = await self.process_file(request)
        existing_document = await self.get_by_id(request.document_id)
        user = await self.user_service.get_auth_user_by_sub(user_permissions.user_id)
        if existing_document:
            history = DocumentHistoryModel(
                document_key=file_name,
                created_at=existing_document.created_at,
                document_id=existing_document.document_id,
                change_reason=request.change_reason,
                version_number=int(existing_document.current_version) + 1,
                change_timestamp=get_current_colombian_time(),
                changed_by=user.user_id,
            )
            await self.document_history_service.create(history)

            existing_document.current_version += 1
            existing_document.document_key = file_name

            await self.update(existing_document)
            await self.message_service.create(
                MessageModel(
                    created_at=get_current_colombian_time(),
                    order_id=existing_document.order_id,
                    title=f"A new version of the file <strong>{existing_document.document_name}</strong> has been uploaded.",
                    message_content=request.change_reason,
                    sender="System",
                    sender_id=None,
                )
            )

            order = VwOrderModel.model_validate(
                await self.order_repository.get_by_id(existing_document.order_id)
            )
            customer = await self.customer_service.get_by_id(order.customer_id)
            business = await self.business_service.get_by_id(order.business_id)

            await self.notification_service.send_file_version_update_notification(
                file_name=existing_document.document_name,
                version=existing_document.current_version,
                notes=request.change_reason,
                customer=customer,
                business=business,
                order=order,
                uploaded_by=user.user_name,
                uploaded_on=get_current_colombian_time(),
            )
