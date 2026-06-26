import logging

from django.conf import settings
from django.core.mail import send_mail
from django.utils.crypto import get_random_string

logger = logging.getLogger(__name__)


def generate_random_password(length=12):
    """Raw password only — caller hashes it via CustomUser.set_password()/create_user()."""
    return get_random_string(length)


def send_credentials_email(user, raw_password, role_label):
    """
    Emails freshly generated login credentials to a new user.
    Raises on failure — callers that shouldn't be blocked by a failed send
    (e.g. Student creation) are expected to catch the exception themselves.
    """
    subject = f"Your {role_label} account has been created"
    message = (
        "Hello,\n\n"
        "An account has been created for you.\n"
        f"Email: {user.email}\n"
        f"Temporary password: {raw_password}\n\n"
        "Please log in and change your password as soon as possible."
    )
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )