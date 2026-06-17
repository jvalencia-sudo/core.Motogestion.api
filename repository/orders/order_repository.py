from typing import Dict, Optional, List, Any
from repository.base_repository import BaseRepository
from domain.models.orders.order import OrderFilterModel


class OrderRepository(BaseRepository):
    """Repository class for handling order-related database operations."""

    def __init__(self):
        super().__init__("orders", "order", "order_id")

    def _build_filter_query(
        self, filters: OrderFilterModel
    ) -> tuple[str, tuple[Any, ...]]:
        """
        Build the SQL query and parameters based on provided filters.

        Args:
            filters: OrderFilterModel object containing filter parameters

        Returns:
            Tuple containing the SQL query and its parameters
        """
        conditions = []
        params: List[Any] = []

        if filters.customer_id is not None:
            conditions.append("customer_id = %s")
            params.append(filters.customer_id)

        if filters.businesses:
            conditions.append("business_id = ANY(%s)")
            params.append(filters.businesses)

        if not conditions:
            return "SELECT * FROM orders.vw_orders", tuple()

        query = f"SELECT * FROM orders.vw_orders WHERE {' AND '.join(conditions)}"
        return query, tuple(params)

    async def get_vw_all(
        self, customer_id: Optional[int] = None, businesses: Optional[List[int]] = None
    ) -> List[Dict]:
        """
        Retrieve all orders with optional filtering by customer_id and businesses.

        Args:
            customer_id: Optional customer ID to filter orders
            businesses: Optional list of business IDs to filter orders

        Returns:
            List of order dictionaries matching the filter criteria

        """
        filters = OrderFilterModel(customer_id=customer_id, businesses=businesses)
        query, params = self._build_filter_query(filters)
        return await self.execute(query, params)

    async def get_by_code(self, code: str) -> Optional[Dict]:
        """
        Retrieve an order by its code.

        Args:
            code: The order code to search for

        Returns:
            Order dictionary if found, None otherwise
        """
        return await self.get_one(
            "SELECT * FROM orders.vw_orders WHERE order_code = %s", (code,)
        )

    async def get_by_id(self, order_id: int) -> Optional[Dict]:
        """
        Retrieve an order by its ID.

        Args:
            order_id: The order ID to search for

        Returns:
            Order dictionary if found, None otherwise
        """
        return await self.get_one(
            "SELECT * FROM orders.vw_orders WHERE order_id = %s", (order_id,)
        )

    async def update_order_process(
        self, order_id: int, process_id: int, order_state_id: int
    ) -> None:
        """
        Update the process and state of an order.

        Args:
            order_id: ID of the order to update
            process_id: New process ID
            order_state_id: New order state ID

        """
        await self.execute_non_query(
            """
            UPDATE orders.order
            SET process_id = %s,
                order_state_id = %s
            WHERE order_id = %s
            """,
            (process_id, order_state_id, order_id),
        )

    async def generate_consecutive(self) -> str:
        """
        Generate a consecutive order number.

        Returns:
            String containing the next consecutive order number
        """
        return await self.get_one(
            "SELECT CONCAT('ORD-', COUNT(*) + 1) AS consecutive FROM orders.order", None
        )
