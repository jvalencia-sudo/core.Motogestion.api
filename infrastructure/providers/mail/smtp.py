import os
import smtplib
from email.message import EmailMessage
from typing import List, Optional

from infrastructure.providers.mail.base_email_provider import BaseEmailProvider


class SMTPEmailProvider(BaseEmailProvider):
    """
    Concrete implementation of BaseEmailProvider using SMTP.
    """

    def __init__(
        self,
        smtp_server: str,
        smtp_port: int,
        username: str,
        password: str,
        use_tls: bool = True,
    ):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.use_tls = use_tls

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
        Private helper method to send an email.

        Args:
            from_email: Sender's email.
            subject: Email subject.
            to_addresses: List of recipient addresses.
            to_cc_addresses: List of CC addresses.
            to_bcc_addresses: List of BCC addresses.
            content: Email content.
            attachments: List of file paths to attach.
            content_type: "text/plain" or "text/html".
            charset: Character encoding.

        Returns:
            None
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

        # Attach files if provided
        if attachments:
            for file_path in attachments:
                try:
                    with open(file_path, "rb") as f:
                        file_data = f.read()
                        file_name = os.path.basename(file_path)
                        msg.add_attachment(
                            file_data,
                            maintype="application",
                            subtype="octet-stream",
                            filename=file_name,
                        )
                except Exception as e:
                    print(f"Failed to attach {file_path}: {e}")

        # Connect to SMTP server and send email
        server = smtplib.SMTP(self.smtp_server, self.smtp_port)
        if self.use_tls:
            server.starttls()
        server.login(self.username, self.password)
        server.send_message(msg)
        server.quit()
        print(f"Email successfully sent to {', '.join(to_addresses)}")

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
        Sends an HTML email.
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
        Sends a plain-text email.
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
