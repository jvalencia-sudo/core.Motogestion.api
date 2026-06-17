from abc import ABC, abstractmethod
from typing import List, Optional


class BaseEmailProvider(ABC):
    @abstractmethod
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

        Args:
            from_email: Sender email address.
            subject: Email subject.
            to_addresses: List of recipient email addresses.
            to_cc_addresses: List of CC recipient email addresses.
            to_bcc_addresses: List of BCC recipient email addresses.
            attachments: List of file paths to attach.
            content: HTML content of the email.
            charset: Character encoding.

        Returns:
            None
        """
        pass

    @abstractmethod
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

        Args:
            from_email: Sender email address.
            subject: Email subject.
            to_addresses: List of recipient email addresses.
            to_cc_addresses: List of CC recipient email addresses.
            to_bcc_addresses: List of BCC recipient email addresses.
            attachments: List of file paths to attach.
            content: Plain text content of the email.
            charset: Character encoding.

        Returns:
            None
        """
        pass
