""" Outbound email helper.

Sends transactional email (currently only password-reset links). Until an
SMTP server is configured the 'log' backend writes the message to the
application log instead of sending, so the rest of the feature can be built
and tested. Set MAIL_BACKEND=smtp (and the MAIL_* settings) to send for
real.
"""
import smtplib
from email.message import EmailMessage

from app import app


def send_email(to_address: str, subject: str, body: str) -> bool:
    """
    Send a plain-text email.

    Args:
        to_address (str): Recipient address.
        subject (str): Subject line.
        body (str): Plain-text body.

    Returns:
        bool: True if sent (or logged) successfully, False on error.
    """
    backend = app.config.get('MAIL_BACKEND', 'log')
    sender = app.config.get('MAIL_FROM', 'noreply@sofistes.net')

    if backend == 'log':
        app.logger.info(
            'MAIL (log backend) to=%s from=%s subject=%s\n%s',
            to_address, sender, subject, body)
        return True

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = to_address
    msg.set_content(body)

    host = app.config.get('MAIL_SERVER', 'localhost')
    port = app.config.get('MAIL_PORT', 25)
    use_tls = app.config.get('MAIL_USE_TLS', False)
    username = app.config.get('MAIL_USERNAME')
    password = app.config.get('MAIL_PASSWORD')

    try:
        with smtplib.SMTP(host, port, timeout=10) as server:
            if use_tls:
                server.starttls()
            if username and password:
                server.login(username, password)
            server.send_message(msg)
        return True
    except (smtplib.SMTPException, OSError) as exp:
        app.logger.error('send_email failed: %s', exp)
        return False
