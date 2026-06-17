import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from config import settings
from domain.contracts.operation.operation_detail_contract import (
    GroupedUnitsContract,
    TotalWeightContract,
)
from domain.contracts.supplier.supplier_contract import EmailContract
from domain.contracts.supplier.supplier_operation_contract import (
    OperationSuppliersContract,
    SupplierCreateEmailsContract,
)
from domain.models.operation.operation_detail_model import VwOperationDetailUnitModel
from domain.models.operation.operation_model import (
    VwOperationWithDetailModel,
    VwOperationModel,
)
from domain.models.supplier.supplier_model import SupplierModel
from domain.models.supplier.supplier_operation_model import SupplierOperationModel
from domain.services.operation.operation_supplier_manager_service import (
    OperationSupplierManagerService,
)
from infrastructure.commons.enums.operation_status import OperationStatus


class TestOperationSupplierManagerService:
    @pytest.fixture
    def service(self) -> OperationSupplierManagerService:
        return OperationSupplierManagerService()

    async def test_get_vw_operation_by_key_returns_operation_with_detail(
        self, service: OperationSupplierManagerService
    ):
        # Arrange
        mock_key = uuid.uuid4()
        mock_operation_id = 123

        mock_supplier_operation = SupplierOperationModel(
            supplier_operation_id=1,
            operation_id=mock_operation_id,
            supplier_id=10,
            key=mock_key,
        )

        mock_operation_detail = VwOperationWithDetailModel(
            operation_code="1223",
            user_id=1,
            requires_escort=True,
            load_date=datetime.now(),
            created_at=datetime.now(),
            validity_date=datetime.now(),
            operation_id=mock_operation_id,
            operation_type_name="Type A",
            location_origin_name="Origin City",
            service_type_name="Service X",
            operation_status_name="Published",
            offer_count=2,
            incoterms=["FOB"],
            hazard_types=["Tóxico"],
            vehicle_types=["Camión"],
            is_local=True,
        )

        service.supplier_operation_service.get_operation_by_key = AsyncMock(
            return_value=mock_supplier_operation
        )
        service.operation_service.get_vw_operations_details_by_operation_id = AsyncMock(
            return_value=mock_operation_detail
        )

        # Act
        result = await service.get_vw_operation_by_key(mock_key)

        # Assert
        assert result == mock_operation_detail
        service.supplier_operation_service.get_operation_by_key.assert_awaited_once_with(
            mock_key
        )
        service.operation_service.get_vw_operations_details_by_operation_id.assert_awaited_once_with(
            mock_operation_id
        )

    async def test_create_operation_suppliers_creates_new_supplier_operation_and_emails(
        self, service: OperationSupplierManagerService
    ):
        # Arrange
        operation_id = 123
        supplier_id = 456
        email_id = 1
        email_str = "test@example.com"

        operation_supplier_contract = OperationSuppliersContract(
            operation_id=operation_id,
            suppliers=[
                SupplierCreateEmailsContract(
                    supplier_id=supplier_id,
                    emails=[
                        EmailContract(
                            email_id=email_id, email=email_str, is_primary=True
                        )
                    ],
                )
            ],
        )

        # Patch dependencies
        service.supplier_operation_service.get_operation_supplier = AsyncMock(
            return_value=None
        )
        service.supplier_operation_service.create = AsyncMock(return_value=999)
        service.supplier_operation_email_service.bulk_create = AsyncMock()
        service.publish_operation = AsyncMock()
        service.operation_service.update_status_operation = AsyncMock()

        # Act
        await service.create_operation_suppliers(operation_supplier_contract)

        # Assert
        service.supplier_operation_service.get_operation_supplier.assert_awaited_once_with(
            operation_id, supplier_id
        )
        service.supplier_operation_service.create.assert_awaited()
        service.supplier_operation_email_service.bulk_create.assert_awaited()
        service.publish_operation.assert_awaited_once()
        service.operation_service.update_status_operation.assert_awaited_once_with(
            operation_id, OperationStatus.Published
        )

    async def test_publish_operation_sends_notification_with_correct_url(
        self, service: OperationSupplierManagerService
    ):
        # Arrange
        operation_id = 123
        supplier_id = 456
        emails = ["proveedor@correo.com"]
        key = uuid.uuid4()

        supplier_operation = SupplierOperationModel(
            operation_id=operation_id,
            supplier_id=supplier_id,
            key=key,
        )

        is_local = True

        service.operation_detail_service.get_detail_of_operation_by_operation_id = (
            AsyncMock(
                return_value=[
                    VwOperationDetailUnitModel(
                        unit_count=10,
                        operation_id=operation_id,
                        unit_weight=12,
                        operation_detail_id=1,
                        unit_type_name="Type A",
                        location_id=1,
                        destination="as",
                    )
                ]
            )
        )
        service.operation_detail_service.group_by_destination = MagicMock(
            return_value=GroupedUnitsContract(
                grouped_by_destination=[],
                total_weight_global=TotalWeightContract(
                    total_net_weight=12, total_gross_weight=12
                ),
            )
        )
        service.operation_service.get_vw_operations_details_by_operation_id = AsyncMock(
            return_value=VwOperationWithDetailModel(
                operation_id=operation_id,
                operation_code="OP-001",
                user_id=1,
                requires_escort=None,
                load_date=datetime.now(),
                created_at=datetime.now(),
                validity_date=datetime.now(),
                operation_type_name="Exportación",
                location_origin_name="Puerto",
                service_type_name="Marítimo",
                operation_status_name="Creada",
                offer_count=0,
                incoterms=[],
                hazard_types=[],
                vehicle_types=[],
                is_local=is_local,
            )
        )
        service.supplier_service.get_by_id = AsyncMock(
            return_value=SupplierModel(
                supplier_id=supplier_id, supplier_name="Test Supplier", status=True
            )
        )
        service.operation_service.get_vw_operation_by_operation_id = AsyncMock(
            return_value=VwOperationModel(
                operation_id=operation_id,
                operation_code="OP-001",
                user_id=1,
                requires_escort=None,
                load_date=datetime.now(),
                created_at=datetime.now(),
                validity_date=datetime.now(),
                operation_type_name="Exportación",
                email="x@y.com",
                location_origin_name="Puerto",
                service_type_name="Marítimo",
                operation_status_name="Creada",
                offer_count=0,
                incoterms=[],
                operation_details=[],
            )
        )
        service.operation_notification_service.send_new_operation_notification = (
            AsyncMock()
        )

        # Act
        await service.publish_operation(
            operation_id, supplier_id, emails, supplier_operation
        )

        # Assert
        service.operation_detail_service.get_detail_of_operation_by_operation_id.assert_awaited_once_with(
            operation_id
        )
        service.operation_service.get_vw_operations_details_by_operation_id.assert_awaited_once_with(
            operation_id
        )
        service.supplier_service.get_by_id.assert_awaited_once_with(supplier_id)
        service.operation_service.get_vw_operation_by_operation_id.assert_awaited_once_with(
            operation_id
        )

        expected_url = (
            f"{settings.quotation_config.national_url}?key={key}"
            if is_local
            else f"{settings.quotation_config.international_url}?key={key}"
        )

        service.operation_notification_service.send_new_operation_notification.assert_awaited_once()
        args, kwargs = (
            service.operation_notification_service.send_new_operation_notification.call_args
        )
        assert args[-1] == expected_url
