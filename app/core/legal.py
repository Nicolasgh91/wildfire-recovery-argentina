"""
Disclaimer legal para módulo VAE.
Decisión D-05: default estático + override dinámico desde API.
"""

DEFAULT_LEGAL_DISCLAIMER = (
    "Los resultados presentados constituyen alertas generadas mediante "
    "detección remota satelital (Sentinel-2) y análisis automatizado de "
    "índices de vegetación. No reemplazan la verificación técnica y legal "
    "presencial. Su interpretación requiere validación por profesionales "
    "habilitados conforme a la ley 26.815 y su modificatoria 27.604."
)


def get_legal_disclaimer(override: str | None = None) -> str:
    """Retorna el disclaimer legal, con posibilidad de override."""
    return override or DEFAULT_LEGAL_DISCLAIMER
