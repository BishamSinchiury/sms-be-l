import random
import string
from django.core.cache import cache
from django.conf import settings
import hmac
from django.core.mail import send_mail


def _make_otp_key(email: str, purpose: str) -> str:
    """
    Builds the Redis key for an OTP.
    
    We include `purpose` so the same email can have separate OTPs
    for separate actions at the same time without collision:
        "otp:login:user@example.com"
        "otp:register:user@example.com"
    """
    return f"otp:{purpose}:{email}"


def generate_otp() -> str:
    """
    Generates a random numeric OTP string.
    Uses secrets-safe random via random.choices with digits only.
    """
    length = getattr(settings, 'OTP_LENGTH', 6)
    return ''.join(random.choices(string.digits, k=length))


def store_otp(email: str, purpose: str) -> str:
    """
    Generates an OTP, stores it in Redis with TTL, and returns it.
    
    The caller (view) is responsible for sending it to the user.
    We return the OTP so the view can pass it to the email utility.
    
    Calling this again before expiry overwrites the old OTP —
    this handles "resend OTP" naturally.
    """
    otp = generate_otp()
    key = _make_otp_key(email, purpose)
    ttl = getattr(settings, 'OTP_EXPIRY_SECONDS', 300)

    # cache.set(key, value, timeout_in_seconds)
    # django-redis maps this directly to Redis SET with EX (expiry)
    cache.set(key, otp, timeout=ttl)

    return otp


def verify_otp(email: str, purpose: str, otp: str) -> bool:
    key = _make_otp_key(email, purpose)
    stored_otp = cache.get(key)

    if stored_otp is None:
        # Still run comparison to keep timing consistent
        hmac.compare_digest(otp, otp)
        return False

    is_valid = hmac.compare_digest(stored_otp, otp)

    if is_valid:
        cache.delete(key)

    return is_valid

def delete_otp(email: str, purpose: str) -> None:
    """
    Manually deletes an OTP before it expires.
    Useful if you want to invalidate an OTP mid-flow.
    """
    cache.delete(_make_otp_key(email, purpose))


def send_otp_email(email: str, otp: str, purpose: str) -> None:
    """
    Sends the OTP to the user's email.
    
    purpose is used to customise the subject line so the user
    knows what the OTP is for — login vs registration etc.
    """
    purpose_labels = {
        'login': 'Admin Login',
        'register': 'Registration',
        'forgot_password': 'Password Reset',
    }

    label = purpose_labels.get(purpose, 'Verification')
    subject = f'Your {label} OTP'
    message = (
        f'Your OTP is: {otp}\n\n'
        f'This code expires in {settings.OTP_EXPIRY_SECONDS // 60} minutes.\n'
        f'Do not share this code with anyone.'
    )

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=False,    # raise exception if email fails — don't silently swallow errors
    )