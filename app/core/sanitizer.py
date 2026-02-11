import re


def redact_pii(message: str) -> str:
    """Redact personally identifiable information from log messages.

    Sanitizes emails, IPs, JWT tokens, API keys, and passwords to comply
    with Argentina's Ley 25.326 (Personal Data Protection) and GDPR.
    """
    if not isinstance(message, str):
        return str(message)

    # Emails: user@example.com -> u***@example.com
    message = re.sub(
        r"[\w.-]+@[\w.-]+\.\w+",
        lambda m: m.group()[0] + "***@" + m.group().split("@")[1],
        message,
    )

    # IPs (IPv4): 192.168.1.100 -> 192.168.1.***
    message = re.sub(
        r"\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.)\d{1,3}\b", r"\1***", message
    )

    # JWT tokens: eyJ... -> [JWT_REDACTED]
    message = re.sub(
        r"eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+",
        "[JWT_REDACTED]",
        message,
    )

    # API Keys: long hex strings (32+ chars)
    message = re.sub(r"\b[a-fA-F0-9]{32,}\b", "[API_KEY_REDACTED]", message)

    # Password values in common patterns
    message = re.sub(
        r'(password|passwd|pwd|secret)["\']?\s*[:=]\s*["\']?[^"\'&\s]+',
        r"\1=[REDACTED]",
        message,
        flags=re.IGNORECASE,
    )

    return message
