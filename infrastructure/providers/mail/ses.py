import logging
import mimetypes
import os
from email.message import EmailMessage
from typing import List, Optional

import boto3

from infrastructure.providers.mail.base_email_provider import BaseEmailProvider

logger = logging.getLogger(__name__)


class SESProvider(BaseEmailProvider):
    """
    Amazon SES v2 Email Provider Implementation with Attachments
    """

    def __init__(self, region_name: str = "us-east-1"):
        """
        Initializes SES Client.
        :param region_name: AWS Region (default: us-east-1)
        """
        self.client = boto3.client("sesv2", region_name=region_name)

    def _send_email(
        self,
        from_email: str,
        subject: str,
        to_addresses: List[str],
        to_cc_addresses: Optional[List[str]],
        to_bcc_addresses: Optional[List[str]],
        content: str,
        attachments: Optional[List[str]],
        content_type: str,
        charset: str,
    ) -> None:
        """
        Internal helper function to send email using SES v2 API (supports attachments).
        """

        msg = EmailMessage()
        msg["From"] = from_email
        msg["To"] = ", ".join(to_addresses)
        if to_cc_addresses:
            msg["Cc"] = ", ".join(to_cc_addresses)
        if to_bcc_addresses:
            msg["Bcc"] = ", ".join(to_bcc_addresses)
        msg["Subject"] = subject
        msg.set_content(content, subtype=content_type)
        msg.set_charset(charset)

        if attachments:
            for file_path in attachments:
                with open(file_path, "rb") as f:
                    file_data = f.read()
                    file_name = os.path.basename(file_path)
                    mime_type, _ = mimetypes.guess_type(file_path)
                    maintype, subtype = (mime_type or "application/octet-stream").split(
                        "/"
                    )
                    msg.add_attachment(
                        file_data,
                        maintype=maintype,
                        subtype=subtype,
                        filename=file_name,
                    )

        self.client.send_email(
            FromEmailAddress=from_email,
            Destination={"ToAddresses": to_addresses},
            Content={"Raw": {"Data": msg.as_bytes()}},
        )

    def send_text_email(
        self,
        from_email: str,
        subject: str,
        to_addresses: List[str],
        to_cc_addresses: Optional[List[str]] = None,
        to_bcc_addresses: Optional[List[str]] = None,
        attachments: Optional[List[str]] = None,
        content: str = "",
        charset: str = "UTF-8",
    ) -> None:
        """
        Sends a plain text email via SES v2
        """
        self._send_email(
            from_email,
            subject,
            to_addresses,
            to_cc_addresses,
            to_bcc_addresses,
            content,
            attachments,
            "plain",
            charset,
        )

    def send_html_email(
        self,
        from_email: str,
        subject: str,
        to_addresses: List[str],
        to_cc_addresses: Optional[List[str]] = None,
        to_bcc_addresses: Optional[List[str]] = None,
        attachments: Optional[List[str]] = None,
        content: str = "",
        charset: str = "UTF-8",
    ) -> None:
        """
        Sends an HTML email via SES v2.
        """
        self._send_email(
            from_email,
            subject,
            to_addresses,
            to_cc_addresses,
            to_bcc_addresses,
            content,
            attachments,
            "html",
            charset,
        )
