import asyncio
import datetime

from faker import Faker

from domain.models.configuration.process_field import ProcessFieldModel
from domain.models.configuration.process_model import ProcessModel
from domain.models.configuration.step_model import StepModel
from domain.models.configuration.step_state_model import StepStateModel
from domain.models.core.customer_model import CustomerModel
from domain.models.orders.order_state_model import OrderStateModel
from repository.base_repository import BaseRepository
from repository.data.db_pool import pool


async def populate_order_state():
    repository = BaseRepository("orders", "order_state", "order_state_id")
    for s in ["Pending Review", "In Progress", "Completed"]:
        os = OrderStateModel(order_state_name=s)
        await repository.create(os)


async def populate_step_state():
    repository = BaseRepository("configuration", "step_state", "step_state_id")
    for s in ["Not started", "In Progress", "Completed"]:
        os = StepStateModel(step_state_name=s)
        await repository.create(os)


async def populate_clients():
    fake = Faker()
    repository = BaseRepository("core", "customer", "customer_id")
    for i in range(100):
        client = CustomerModel(
            customer_name=fake.name(),
            customer_code="".join(fake.random_letters(length=10)),
            email=fake.email(),
            created_at=fake.date_time(),
            default_language="en",
        )
        await repository.create(client)


async def populate_process():
    repository = BaseRepository("configuration", "process", "process_id")
    process = ProcessModel(
        process_name="International shipping",
        created_at=datetime.datetime.now(),
        business_id=None,
        description="International shipping process",
    )

    _id = await repository.create(process)
    process_steps = [
        StepModel(
            process_id=_id,
            step_name="Order placement",
            visible_to_customer=True,
            step_order=1,
            created_at=datetime.datetime.now(),
        ),
        StepModel(
            process_id=_id,
            step_name="Booking",
            visible_to_customer=True,
            step_order=1,
            created_at=datetime.datetime.now(),
        ),
        StepModel(
            process_id=_id,
            step_name="Available documents",
            visible_to_customer=True,
            step_order=1,
            created_at=datetime.datetime.now(),
        ),
        StepModel(
            process_id=_id,
            step_name="Departure",
            visible_to_customer=True,
            step_order=1,
            created_at=datetime.datetime.now(),
        ),
        StepModel(
            process_id=_id,
            step_name="Documents shipping",
            visible_to_customer=True,
            step_order=1,
            created_at=datetime.datetime.now(),
        ),
        StepModel(
            process_id=_id,
            step_name="Documents arrived to final destination",
            visible_to_customer=True,
            step_order=1,
            created_at=datetime.datetime.now(),
        ),
    ]
    step_repo = BaseRepository("configuration", "step", "step_id")
    for step in process_steps:
        await step_repo.create(step)

    process_fields = [
        ProcessFieldModel(
            process_id=_id,
            field_name="Tracking number",
            created_at=datetime.datetime.now(),
        ),
        ProcessFieldModel(
            process_id=_id,
            field_name="Freight number",
            created_at=datetime.datetime.now(),
        ),
        ProcessFieldModel(
            process_id=_id,
            field_name="Documents shipping number",
            created_at=datetime.datetime.now(),
        ),
    ]

    field_repo = BaseRepository("configuration", "process_fields", "process_field_id")
    for field in process_fields:
        await field_repo.create(field)


async def main():
    await pool.open()
    await populate_clients()
    await populate_order_state()
    await populate_step_state()
    await populate_process()
    await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
