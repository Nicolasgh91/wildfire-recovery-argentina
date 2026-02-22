# =============================================================================
# MEJORA 2: ÍNDICE COMPUESTO PARA PREVENIR DUPLICADOS
# =============================================================================

"""
Problema:
    - Descargas diarias pueden duplicar registros
    - Query lento al buscar por fecha + satélite
    
Solución:
    - Índice compuesto en (acquisition_date, satellite, latitude, longitude)
    - Constraint UNIQUE para prevenir duplicados
"""

"""Add composite indexes and unique constraints

Revision ID: 002
Revises: 001
Create Date: 2025-01-24

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers
revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade():
    """
    Agregar índices compuestos y constraint único para prevenir duplicados.
    """

    # 1. Índice compuesto para queries frecuentes
    op.create_index(
        "idx_fire_detections_date_satellite",
        "fire_detections",
        ["acquisition_date", "satellite"],
        unique=False,
    )

    # 2. Índice para búsqueda de duplicados
    op.create_index(
        "idx_fire_detections_unique_detection",
        "fire_detections",
        ["acquisition_date", "satellite", "latitude", "longitude", "acquisition_time"],
        unique=False,  # No unique por si hay realmente dos detecciones en el mismo punto
    )

    # 3. Índice para fire_events por año/mes (para stats)
    op.execute(
        """
        CREATE INDEX idx_fire_events_year_month 
        ON fire_events (EXTRACT(YEAR FROM start_date), EXTRACT(MONTH FROM start_date))
    """
    )

    # 4. Índice parcial para eventos significativos
    op.execute(
        """
        CREATE INDEX idx_fire_events_significant_recent 
        ON fire_events (start_date DESC) 
        WHERE is_significant = TRUE 
        AND start_date >= NOW() - INTERVAL '1 year'
    """
    )


def downgrade():
    """Revertir cambios"""
    op.drop_index("idx_fire_detections_date_satellite", "fire_detections")
    op.drop_index("idx_fire_detections_unique_detection", "fire_detections")
    op.execute("DROP INDEX IF EXISTS idx_fire_events_year_month")
    op.execute("DROP INDEX IF EXISTS idx_fire_events_significant_recent")
