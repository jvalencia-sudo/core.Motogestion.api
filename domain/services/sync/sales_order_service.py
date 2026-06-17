from domain.models.core.business_model import BusinessModel
from domain.models.core.customer_model import CustomerModel
from domain.models.core.product_model import ProductModel
from domain.models.orders.order_model import OrderModel
from domain.models.orders.order_product_model import OrderProductModel
from domain.models.sync.sales_order_model import (
    SalesOrderModel,
    VwSalesOrderWithoutDetailsModel,
)
from domain.services.base_service import BaseService
from domain.services.core.business_service import BusinessService
from domain.services.core.customer_service import CustomerService
from domain.services.core.product_service import ProductService
from domain.services.orders.order_product_service import OrderProductService
from domain.services.orders.order_service import OrderService
from infrastructure.commons.enums.order_state import OrderStateEnum
from infrastructure.exceptions.domain_exception import DomainException
from infrastructure.utils.date import get_current_colombian_time
from repository.sync.sales_orders_repository import SalesOrdersRepository


class SalesOrderService(BaseService[SalesOrderModel, SalesOrdersRepository]):
    def __init__(self):
        super().__init__(SalesOrdersRepository())
        self.customer_service = CustomerService()
        self.business_service = BusinessService()
        self.product_service = ProductService()
        self.order_service = OrderService()
        self.order_product = OrderProductService()

    def __parse__(self, record: dict) -> SalesOrderModel:
        return SalesOrderModel.model_validate(record)

    async def get_by_order_number(self, order_number: str) -> list[SalesOrderModel]:
        return self.__parse_all__(
            await self.repository.get_by_order_number(order_number)
        )

    async def get_all_without_details(self) -> list[VwSalesOrderWithoutDetailsModel]:
        return self.__parse_all_custom__(
            await self.repository.get_all_without_details(),
            VwSalesOrderWithoutDetailsModel,
        )

    async def create_order_from_sales_order(self, order_number: str) -> str:
        sales_orders = await self.get_by_order_number(order_number)

        if len(sales_orders) == 0:
            raise DomainException("Sales order not found")

        customers = set([so.customer for so in sales_orders])
        if len(customers) > 1:
            raise DomainException("Multiple customers found")

        business = await self.business_service.get_or_create(
            BusinessModel(
                business_name=sales_orders[0].sales_organization,
                code=sales_orders[0].sales_organization,
            )
        )

        customer = await self.customer_service.get_or_create(
            CustomerModel(
                customer_code=sales_orders[0].customer,
                customer_name=sales_orders[0].customer_name,
                created_at=get_current_colombian_time(),
                email=f"{sales_orders[0].customer}@not-configured.com",
                default_language="es",
                business_id=business.business_id,
            )
        )

        business = await self.business_service.get_by_code(
            sales_orders[0].sales_organization
        )

        if not business:
            raise DomainException("Business not found")

        products = await self.product_service.get_or_create_all(
            [
                ProductModel(
                    code=p.material_code,
                    product_name=p.material,
                    description=p.material,
                    business_id=business.business_id,
                )
                for p in sales_orders
            ]
        )

        order = await self.order_service.create_order(
            OrderModel(
                created_at=get_current_colombian_time(),
                order_code="",
                customer_id=customer.customer_id,
                business_id=business.business_id,
                order_state_id=OrderStateEnum.PendingReview,
                process_id=None,
                description=None,
            )
        )

        for p in products:
            product = next(s for s in sales_orders if s.material_code == p.code)
            await self.order_product.create(
                OrderProductModel(
                    order_id=order.order_id,
                    product_id=p.product_id,
                    quantity=product.requested_quantity,
                    unit_of_measure=product.unit_of_measure,
                )
            )

        return order.order_code
