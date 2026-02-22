"""
=============================================================================
FORESTGUARD - CENTRALIZED EMAIL NOTIFICATION CONFIGURATION
=============================================================================

This file contains ALL email addresses used throughout the ForestGuard project.
To change notification recipients, modify ONLY this file.

Documentation:
- User Manual (EN): docs/USER_MANUAL.md (Section: Email Notifications)
- Manual de Usuario (ES): docs/MANUAL_DE_USUARIO.md (Sección: Notificaciones)

Author: ForestGuard Dev Team
Version: 1.0.0
Last Updated: 2026-01-29
=============================================================================
"""

from typing import List, Optional


class EmailConfig:
    """
    Centralized email configuration for all ForestGuard notifications.

    Usage:
        from app.core.email_config import email_config

        recipient = email_config.ADMIN_EMAIL
        notify_list = email_config.CITIZEN_REPORTS_NOTIFY
    """

    # =========================================================================
    # ADMIN NOTIFICATIONS
    # =========================================================================

    # Primary admin email - receives security alerts and system notifications
    ADMIN_EMAIL: str = "nicolasgabrielh91@gmail.com"

    # =========================================================================
    # CITIZEN REPORTS (UC-09)
    # =========================================================================

    # Emails to notify when new citizen reports are submitted
    CITIZEN_REPORTS_NOTIFY: List[str] = ["nicolasgabrielh91@gmail.com"]

    # From address for citizen report acknowledgments (sent to reporter)
    CITIZEN_REPORTS_FROM: str = "noreply@forestguard.freedynamicdns.org"

    # Subject prefix for citizen report emails
    CITIZEN_REPORTS_SUBJECT_PREFIX: str = "[ForestGuard] Nueva Denuncia"

    # =========================================================================
    # LAND USE CHANGE ALERTS (UC-08)
    # =========================================================================

    # Emails to notify when illegal land use change is detected
    LAND_USE_VIOLATION_NOTIFY: List[str] = ["nicolasgabrielh91@gmail.com"]

    # Subject prefix for land use violation alerts
    LAND_USE_VIOLATION_SUBJECT_PREFIX: str = "[ForestGuard] ⚠️ Posible Violación"

    # =========================================================================
    # SECURITY ALERTS
    # =========================================================================

    # Email for rate limit violations and security alerts
    SECURITY_ALERTS_TO: str = "nicolasgabrielh91@gmail.com"

    # Subject prefix for security alerts
    SECURITY_ALERTS_SUBJECT_PREFIX: str = "[ForestGuard] 🔒 Alerta de Seguridad"

    # =========================================================================
    # CERTIFICATE NOTIFICATIONS (UC-07)
    # =========================================================================

    # CC email for all certificate generations (audit trail)
    # Set to None to disable CC
    CERTIFICATE_CC: Optional[str] = None

    # From address for certificate emails
    CERTIFICATE_FROM: str = "certificados@forestguard.freedynamicdns.org"

    # =========================================================================
    # JUDICIAL REPORTS (UC-02)
    # =========================================================================

    # Notification when judicial report is generated
    # Set to None to disable notification
    JUDICIAL_REPORTS_NOTIFY: Optional[str] = None

    # From address for judicial report emails
    JUDICIAL_REPORTS_FROM: str = "peritajes@forestguard.freedynamicdns.org"

    # =========================================================================
    # SYSTEM NOTIFICATIONS
    # =========================================================================

    # Default from address for all system emails
    DEFAULT_FROM: str = "sistema@forestguard.freedynamicdns.org"

    # Reply-to address for support inquiries
    SUPPORT_REPLY_TO: str = "nicolasgabrielh91@gmail.com"

    # =========================================================================
    # EMAIL TEMPLATES
    # =========================================================================

    # Base URL for email template assets
    EMAIL_ASSETS_BASE_URL: str = "https://forestguard.freedynamicdns.org/assets"

    # Logo URL for email headers
    EMAIL_LOGO_URL: str = (
        "https://forestguard.freedynamicdns.org/assets/logo/logo-horizontal.png"
    )


# Singleton instance - import this in your code
email_config = EmailConfig()
