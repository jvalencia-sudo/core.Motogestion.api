import datetime

from domain.models.configuration.step_model import StepModel
from domain.models.configuration.step_state_model import StepStateModel
from domain.models.core.business_model import BusinessModel
from domain.models.core.customer_model import CustomerModel
from domain.models.orders.order_model import VwOrderModel
from domain.services.core.customer_preferences_service import CustomerPreferencesService
from infrastructure.providers.mail.base_email_provider import BaseEmailProvider
from infrastructure.providers.mail.ses import SESProvider
from infrastructure.templating.base_template_engine import BaseTemplateEngine
from infrastructure.templating.jinja_template_engine import JinjaI18nRenderer
from config import settings


# TODO: Figure out if its necessary to create and abstract class and call this class like SESAndJinjaNotificationService
class NotificationService:
    def __init__(self):
        self.email_provider: BaseEmailProvider = SESProvider()
        self.template_engine: BaseTemplateEngine = JinjaI18nRenderer()
        self.customer_preferences = CustomerPreferencesService()
        # TODO: Assign a default email to each company
        # FIXME
        self.default_from_email = "no-reply@iluma.solutions"

    async def send_new_file_uploaded_notification(
        self,
        file_name: str,
        notes: str,
        customer: CustomerModel,
        business: BusinessModel,
        order: VwOrderModel,
        uploaded_by: str,
        uploaded_on: datetime.datetime,
    ):
        preferences = await self.customer_preferences.get_by_id(customer.customer_id)
        if preferences is None or preferences.allow_new_file_uploaded_notification:
            self.template_engine.set_language(customer.default_language)
            template = self.template_engine.render_template(
                "new_file_uploaded_email_template.html",
                notes=notes,
                business=business,
                customer=customer,
                order=order,
                file_name=file_name,
                uploaded_by=uploaded_by,
                uploaded_on=uploaded_on,
                environment=settings.frontend_url,
            )
            self.email_provider.send_html_email(
                self.default_from_email,
                "Order update notification",
                to_addresses=[customer.email],
                content=template,
            )

    async def send_order_status_email_notification(
        self,
        notes: str,
        customer: CustomerModel,
        business: BusinessModel,
        order: VwOrderModel,
        state: StepStateModel,
        step: StepModel,
        update_on: datetime.datetime,
    ):
        preferences = await self.customer_preferences.get_by_id(customer.customer_id)
        if preferences is None or preferences.allow_order_status_update_notification:
            self.template_engine.set_language(customer.default_language)
            template = self.template_engine.render_template(
                "status_update_email_template.html",
                notes=notes,
                business=business,
                customer=customer,
                order=order,
                state=state,
                step=step,
                update_on=update_on,
                environment=settings.frontend_url,
            )
            self.email_provider.send_html_email(
                self.default_from_email,
                "Order update notification",
                to_addresses=[customer.email],
                content=template,
            )

    async def send_order_message_notification(
        self,
        message_content: str,
        message_from: str,
        customer: CustomerModel,
        business: BusinessModel,
        order: VwOrderModel,
        posted_on: datetime.datetime,
    ):
        preferences = await self.customer_preferences.get_by_customer_id(
            customer.customer_id
        )
        if preferences is None or preferences.allow_order_messages_notification:
            self.template_engine.set_language(customer.default_language)
            template = self.template_engine.render_template(
                "order_message_email_template.html",
                message_content=message_content,
                message_from=message_from,
                business=business,
                customer=customer,
                order=order,
                posted_on=posted_on,
                environment=settings.frontend_url,
            )
            self.email_provider.send_html_email(
                self.default_from_email,
                "New order message notification",
                to_addresses=[customer.email],
                content=template,
            )

    async def send_file_version_update_notification(
        self,
        file_name: str,
        version: str,
        notes: str,
        customer: CustomerModel,
        business: BusinessModel,
        order: VwOrderModel,
        uploaded_by: str,
        uploaded_on: datetime.datetime,
    ):
        preferences = await self.customer_preferences.get_by_id(customer.customer_id)
        if (
            preferences is None
            or preferences.allow_new_file_version_uploaded_notification
        ):
            self.template_engine.set_language(customer.default_language)
            template = self.template_engine.render_template(
                "file_version_update_email_template.html",
                notes=notes,
                business=business,
                customer=customer,
                order=order,
                file_name=file_name,
                version=version,
                uploaded_by=uploaded_by,
                uploaded_on=uploaded_on,
                environment=settings.frontend_url,
            )
            self.email_provider.send_html_email(
                self.default_from_email,
                "File version update notification",
                to_addresses=[customer.email],
                content=template,
            )
