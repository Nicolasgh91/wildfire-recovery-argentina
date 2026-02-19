class BrandSettings:
    """
    Global Branding Configuration for Backend.
    
    This class serves as the single source of truth for the application's branding
    in the backend (reports, emails, templates, etc.).
    """
    
    # The visible name of the application
    APP_NAME = "Vestigia"
    
    # The application's tagline
    APP_TAGLINE = "Wildfire Recovery & Monitoring"
    
    # The public URL of the application (used in links, emails)
    # Keeping the original domain for now to preserve availability
    APP_PUBLIC_URL = "https://forestguard.freedynamicdns.org"
    
    # Internal branding slug (lowercase, no spaces)
    APP_BRAND_SLUG = "vestigia"
    
    # Support email or contact info
    APP_SUPPORT_EMAIL = "admin@forestguard.freedynamicdns.org"

brand = BrandSettings()
