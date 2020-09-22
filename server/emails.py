"""Manage sending emails."""
import smtplib
import ssl

from config import (
    EMAIL_ADDRESS, SMTP_PASSWORD, SMTP_PORT, SMTP_SERVER, SMTP_USERNAME
)

context = ssl.create_default_context()


def send_email(address: str, content: str, subject: str):
    """Attempt to send an email to some address."""
    message = (
        f'From: {EMAIL_ADDRESS}\n'
        f'To: {address}\n'
        f'Subject: {subject}\n\n'
        f'{content}'
    )
    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=context) as server:
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.sendmail(EMAIL_ADDRESS, address, message)
