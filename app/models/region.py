"""
=============================================================================
FORESTGUARD API - MODELOS DE REGIONES Y ÁREAS PROTEGIDAS
=============================================================================

Este módulo define las entidades geográficas para la fiscalización legal:

1. Region: Divisiones políticas (Provincias, Departamentos)
   - Fuente: IGN Argentina
   - Uso: Enriquecer fire_events con ubicación administrativa

2. ProtectedArea: Áreas protegidas (Parques Nacionales, Reservas, etc.)
   - Fuente: IGN / APN / Protected Planet (WDPA)
   - Uso: Calcular prohibiciones legales según Ley 26.815

3. FireProtectedAreaIntersection: Relación N:M entre incendios y áreas
   - Almacena la intersección geométrica
   - Calcula prohibition_until (fecha fin de prohibición)

Marco Legal (Ley 26.815 Art. 22 bis):
-------------------------------------
    - Bosques nativos y áreas protegidas: 60 años de prohibición
    - Zonas agrícolas/praderas: 30 años de prohibición
    
    La prohibición impide cambio de uso del suelo (loteo, construcción,
    agricultura) en terrenos afectados por incendios.

Categorías IUCN soportadas:
---------------------------
    - Ia: Reserva Natural Estricta
    - Ib: Área Silvestre  
    - II: Parque Nacional
    - III: Monumento Natural
    - IV: Área de Manejo de Hábitat/Especies
    - V: Paisaje Protegido
    - VI: Área Protegida con uso sostenible de recursos naturales
=============================================================================
"""

from datetime import date
from typing import TYPE_CHECKING, List, Optional

from geoalchemy2 import Geography
from sqlalchemy import (
    CheckConstraint,
    Column,
    Date,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

# Ajusta los imports según tu estructura de proyecto
try:
    from app.db.base import Base, TimestampMixin, UUIDMixin
except ImportError:
    from app.db.base import Base

    TimestampMixin = object
    UUIDMixin = object

if TYPE_CHECKING:
    from app.models.fire import FireEvent


# =============================================================================
# CONSTANTES - Categorías válidas
# =============================================================================

PROTECTED_AREA_CATEGORIES = (
    "national_park",  # Parque Nacional (IUCN II)
    "national_reserve",  # Reserva Nacional
    "natural_monument",  # Monumento Natural (IUCN III)
    "provincial_reserve",  # Reserva Provincial
    "provincial_park",  # Parque Provincial
    "biosphere_reserve",  # Reserva de Biosfera (UNESCO-MAB)
    "ramsar_site",  # Sitio Ramsar (Convención de Humedales)
    "world_heritage",  # Patrimonio Mundial Natural (UNESCO)
    "municipal_reserve",  # Reserva Municipal
    "private_reserve",  # Reserva Natural Privada
    "wildlife_refuge",  # Refugio de Vida Silvestre
    "marine_park",  # Parque Marino
    "other",  # Otras categorías
)

JURISDICTION_TYPES = ("national", "provincial", "municipal", "private")

REGION_CATEGORIES = ("PROVINCIA", "DEPARTAMENTO", "MUNICIPIO")


# =============================================================================
# MODELO: REGION (Divisiones Políticas)
# =============================================================================


class Region(Base):
    """
    Divisiones político-administrativas de Argentina.

    Almacena los polígonos de provincias y departamentos para:
    - Enriquecer fire_events con información de ubicación
    - Generar estadísticas por jurisdicción
    - Filtrar consultas por región

    Fuente de datos:
        Instituto Geográfico Nacional (IGN)
        API Georef: https://apis.datos.gob.ar/georef/api/

    Ejemplo de uso:
        >>> # Encontrar en qué provincia está un incendio
        >>> province = db.query(Region).filter(
        ...     Region.category == 'PROVINCIA',
        ...     func.ST_Contains(Region.geom, fire.centroid)
        ... ).first()

    Attributes:
        id: Identificador único (autoincremental)
        name: Nombre de la región (ej: "Córdoba", "La Matanza")
        category: Tipo de región ("PROVINCIA", "DEPARTAMENTO", "MUNICIPIO")
        geom: Geometría MultiPolygon en WGS84 (EPSG:4326)
    """

    __tablename__ = "regions"

    # -------------------------------------------------------------------------
    # Columnas
    # -------------------------------------------------------------------------
    id = Column(
        Integer, primary_key=True, autoincrement=True, doc="ID único de la región"
    )

    name = Column(
        String(255),
        nullable=False,
        index=True,
        doc="Nombre oficial de la región (ej: 'Córdoba')",
    )

    category = Column(
        String(50),
        nullable=False,
        index=True,
        doc="Tipo: PROVINCIA, DEPARTAMENTO o MUNICIPIO",
    )

    """  
  # Geometría: MultiPolygon para soportar islas o territorios discontinuos
    geom = Column(
        Geography(geometry_type='MULTIPOLYGON', srid=4326), 
        nullable=False,
        doc="Límites geográficos (WGS84)"
    )
    """

    geom = Column(
        Geography(geometry_type="MULTIPOLYGON", srid=4326, spatial_index=False),
        nullable=False,
        doc="Límites geográficos (WGS84)",
    )

    # -------------------------------------------------------------------------
    # Índices y Constraints
    # -------------------------------------------------------------------------
    __table_args__ = (
        # Índice espacial GIST para consultas geográficas rápidas
        Index("idx_regions_geom", geom, postgresql_using="gist"),
        # Índice compuesto para búsquedas por categoría + nombre
        Index("idx_regions_category_name", category, name),
        # Validar categorías permitidas
        CheckConstraint(
            f"category IN {REGION_CATEGORIES}", name="ck_regions_valid_category"
        ),
    )

    def __repr__(self) -> str:
        return f"<Region(id={self.id}, name='{self.name}', category='{self.category}')>"


# =============================================================================
# MODELO: PROTECTED AREA (Áreas Protegidas)
# =============================================================================


class ProtectedArea(Base, UUIDMixin, TimestampMixin):
    """
    Áreas protegidas de Argentina.

    Incluye Parques Nacionales, Reservas Provinciales, Monumentos Naturales,
    Sitios Ramsar, Reservas de Biosfera y otras categorías de protección.

    Fuentes de datos:
        - IGN: https://www.ign.gob.ar/NuestrasActividades/InformacionGeoespacial/CapasSIG
        - APN: https://mapas.parquesnacionales.gob.ar/
        - WDPA: https://www.protectedplanet.net/country/ARG

    La columna `prohibition_years` define el período de prohibición según
    la Ley 26.815 Art. 22 bis:
        - 60 años: Parques nacionales, reservas, bosques nativos
        - 30 años: Otras zonas (agrícolas, praderas)

    Ejemplo de uso:
        >>> # Verificar si un punto está en área protegida
        >>> area = db.query(ProtectedArea).filter(
        ...     func.ST_Intersects(ProtectedArea.boundary, point)
        ... ).first()
        >>>
        >>> if area:
        ...     from datetime import timedelta
        ...     prohibition_until = fire_date + timedelta(days=area.prohibition_years * 365)

    Attributes:
        id: UUID único
        official_name: Nombre oficial del área
        category: Categoría de protección (national_park, provincial_reserve, etc.)
        boundary: Polígono/MultiPolígono del área
        prohibition_years: Años de prohibición (60 o 30)
        jurisdiction: Jurisdicción (national, provincial, municipal)
    """

    __tablename__ = "protected_areas"

    # -------------------------------------------------------------------------
    # Identificación
    # -------------------------------------------------------------------------
    official_name = Column(
        String(255), nullable=False, index=True, doc="Nombre oficial del área protegida"
    )

    alternative_names = Column(ARRAY(Text), doc="Nombres alternativos o históricos")

    category = Column(
        String(50),
        nullable=False,
        index=True,
        doc="Categoría de protección según IUCN/WDPA",
    )

    # -------------------------------------------------------------------------
    # Geometría
    # -------------------------------------------------------------------------
    boundary = Column(
        Geography(geometry_type="MULTIPOLYGON", srid=4326, spatial_index=False),
        nullable=False,
        doc="Límites oficiales del área (MultiPolygon WGS84)",
    )

    simplified_boundary = Column(
        Geography(geometry_type="POLYGON", srid=4326),
        doc="Límites simplificados para consultas rápidas (ST_Simplify 100m)",
    )

    centroid = Column(
        Geography(geometry_type="POINT", srid=4326), doc="Centro geográfico del área"
    )

    area_hectares = Column(Float, doc="Superficie total en hectáreas")

    # -------------------------------------------------------------------------
    # Información Administrativa
    # -------------------------------------------------------------------------
    jurisdiction = Column(
        String(50), doc="Jurisdicción: national, provincial, municipal, private"
    )

    province = Column(String(100), index=True, doc="Provincia donde se ubica el área")

    department = Column(String(100), doc="Departamento/Partido donde se ubica")

    # -------------------------------------------------------------------------
    # Marco Legal (Ley 26.815)
    # -------------------------------------------------------------------------
    prohibition_years = Column(
        Integer,
        nullable=False,
        default=60,
        doc="Años de prohibición según Ley 26.815 (60 para bosques, 30 otros)",
    )

    carrying_capacity = Column(
        Integer,
        nullable=True,
        doc="Capacidad de carga estimada para alertas preventivas (UC-04)",
    )

    # -------------------------------------------------------------------------
    # Metadata e Interoperabilidad
    # -------------------------------------------------------------------------
    established_date = Column(Date, doc="Fecha de creación/establecimiento del área")

    managing_authority = Column(
        String(200), doc="Autoridad de gestión (APN, Gobierno Provincial, etc.)"
    )

    # Campos para compatibilidad con WDPA (Protected Planet)
    wdpa_id = Column(
        Integer, unique=True, doc="ID en World Database on Protected Areas"
    )

    iucn_category = Column(
        String(10), doc="Categoría IUCN (Ia, Ib, II, III, IV, V, VI)"
    )

    source_dataset = Column(String(100), doc="Dataset de origen (IGN, APN, WDPA)")

    source_url = Column(Text, doc="URL del dataset original")

    # -------------------------------------------------------------------------
    # Relaciones
    # -------------------------------------------------------------------------
    fire_intersections: Mapped[List["FireProtectedAreaIntersection"]] = relationship(
        "FireProtectedAreaIntersection",
        back_populates="protected_area",
        cascade="all, delete-orphan",
    )

    # -------------------------------------------------------------------------
    # Índices y Constraints
    # -------------------------------------------------------------------------
    __table_args__ = (
        # Índices espaciales GIST
        Index("idx_protected_areas_boundary", boundary, postgresql_using="gist"),
        Index(
            "idx_protected_areas_simplified",
            simplified_boundary,
            postgresql_using="gist",
        ),
        # Validar categorías
        CheckConstraint(
            f"category IN {PROTECTED_AREA_CATEGORIES}",
            name="ck_protected_areas_valid_category",
        ),
        # Validar jurisdicción
        CheckConstraint(
            f"jurisdiction IS NULL OR jurisdiction IN {JURISDICTION_TYPES}",
            name="ck_protected_areas_valid_jurisdiction",
        ),
        # Validar años de prohibición
        CheckConstraint(
            "prohibition_years IN (30, 60)", name="ck_protected_areas_valid_prohibition"
        ),
    )

    # -------------------------------------------------------------------------
    # Propiedades Computadas
    # -------------------------------------------------------------------------
    @property
    def display_name(self) -> str:
        """Nombre formateado para mostrar con categoría."""
        category_display = {
            "national_park": "Parque Nacional",
            "national_reserve": "Reserva Nacional",
            "natural_monument": "Monumento Natural",
            "provincial_reserve": "Reserva Provincial",
            "provincial_park": "Parque Provincial",
            "biosphere_reserve": "Reserva de Biosfera",
            "ramsar_site": "Sitio Ramsar",
            "world_heritage": "Patrimonio Mundial",
            "municipal_reserve": "Reserva Municipal",
            "private_reserve": "Reserva Privada",
            "wildlife_refuge": "Refugio de Vida Silvestre",
            "marine_park": "Parque Marino",
        }
        prefix = category_display.get(self.category, self.category)
        return f"{prefix} {self.official_name}"

    def __repr__(self) -> str:
        return (
            f"<ProtectedArea(name='{self.official_name}', category='{self.category}')>"
        )


# =============================================================================
# MODELO: FIRE-PROTECTED AREA INTERSECTION
# =============================================================================


class FireProtectedAreaIntersection(Base, UUIDMixin, TimestampMixin):
    """
    Intersección entre un evento de incendio y un área protegida.

    Esta tabla de relación N:M almacena:
    - El vínculo entre un incendio y el área protegida afectada
    - La geometría de la intersección (opcional)
    - La fecha de prohibición calculada

    Cálculo de prohibition_until:
        prohibition_until = fire_date + (prohibition_years * 365 días)

        Ejemplo: Incendio en Parque Nacional el 2024-08-15
        → prohibition_until = 2084-08-15 (60 años después)

    Ejemplo de uso:
        >>> from datetime import timedelta
        >>> intersection = FireProtectedAreaIntersection(
        ...     fire_event_id=fire.id,
        ...     protected_area_id=area.id,
        ...     fire_date=fire.start_date.date(),
        ...     prohibition_until=fire.start_date.date() + timedelta(days=60*365)
        ... )
        >>> db.add(intersection)

    Attributes:
        fire_event_id: FK al evento de incendio
        protected_area_id: FK al área protegida
        fire_date: Fecha del incendio (inicio de prohibición)
        prohibition_until: Fecha fin de la prohibición
        intersection_area_hectares: Área afectada dentro del área protegida
    """

    __tablename__ = "fire_protected_area_intersections"

    # -------------------------------------------------------------------------
    # Foreign Keys
    # -------------------------------------------------------------------------
    fire_event_id = Column(
        UUID(as_uuid=True),
        ForeignKey("fire_events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="FK al evento de incendio",
    )

    protected_area_id = Column(
        UUID(as_uuid=True),
        ForeignKey("protected_areas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="FK al área protegida",
    )

    # -------------------------------------------------------------------------
    # Geometría de Intersección
    # -------------------------------------------------------------------------
    intersection_geometry = Column(
        Geography(geometry_type="POLYGON", srid=4326),
        doc="Polígono de intersección (fuego ∩ área protegida)",
    )

    intersection_area_hectares = Column(
        Float, doc="Superficie de la intersección en hectáreas"
    )

    overlap_percentage = Column(
        Float, doc="Porcentaje del área del fuego dentro del área protegida"
    )

    # -------------------------------------------------------------------------
    # Información Legal
    # -------------------------------------------------------------------------
    fire_date = Column(
        Date, nullable=False, doc="Fecha del incendio (inicio de la prohibición)"
    )

    prohibition_until = Column(
        Date,
        nullable=False,
        index=True,
        doc="Fecha hasta la cual aplica la prohibición",
    )

    # -------------------------------------------------------------------------
    # Relaciones
    # -------------------------------------------------------------------------
    fire_event: Mapped["FireEvent"] = relationship(
        "FireEvent", back_populates="protected_area_intersections"
    )

    protected_area: Mapped["ProtectedArea"] = relationship(
        "ProtectedArea", back_populates="fire_intersections"
    )

    # -------------------------------------------------------------------------
    # Índices y Constraints
    # -------------------------------------------------------------------------
    __table_args__ = (
        # Evitar duplicados
        UniqueConstraint(
            "fire_event_id", "protected_area_id", name="uq_fire_protected_area"
        ),
        # Índice para consultas de prohibiciones activas
        Index(
            "idx_fire_pa_active_prohibitions",
            prohibition_until,
        ),
    )

    # -------------------------------------------------------------------------
    # Propiedades Computadas
    # -------------------------------------------------------------------------
    @property
    def is_prohibition_active(self) -> bool:
        """Verifica si la prohibición sigue vigente."""
        return self.prohibition_until > date.today()

    @property
    def years_remaining(self) -> int:
        """Años restantes de prohibición (0 si ya expiró)."""
        if not self.is_prohibition_active:
            return 0
        delta = self.prohibition_until - date.today()
        return delta.days // 365

    @property
    def days_remaining(self) -> int:
        """Días restantes de prohibición (0 si ya expiró)."""
        if not self.is_prohibition_active:
            return 0
        return (self.prohibition_until - date.today()).days

    def __repr__(self) -> str:
        return (
            f"<FireProtectedAreaIntersection("
            f"fire={self.fire_event_id}, "
            f"area={self.protected_area_id}, "
            f"until={self.prohibition_until})>"
        )
