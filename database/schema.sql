-- Habilitar extensión PostGIS si no está habilitada
CREATE EXTENSION IF NOT EXISTS postgis;

-- Tabla principal de incendios
CREATE TABLE incendios (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fecha_deteccion DATE NOT NULL,
    provincia VARCHAR(100),
    localidad VARCHAR(100),
    latitud DECIMAL(10, 8) NOT NULL,
    longitud DECIMAL(11, 8) NOT NULL,
    area_afectada_hectareas DECIMAL(10, 2),
    geometria GEOMETRY(Polygon, 4326), -- WGS84
    tipo VARCHAR(20) CHECK (tipo IN ('nuevo', 'recurrente')) DEFAULT 'nuevo',
    incendio_previo_id UUID REFERENCES incendios(id),
    estado_analisis VARCHAR(20) CHECK (estado_analisis IN ('pendiente', 'procesando', 'completado', 'error')) DEFAULT 'pendiente',
    error_mensaje TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tabla de análisis mensual (36 meses post-incendio)
CREATE TABLE analisis_mensual (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    incendio_id UUID NOT NULL REFERENCES incendios(id) ON DELETE CASCADE,
    mes_numero INTEGER NOT NULL CHECK (mes_numero BETWEEN 1 AND 36),
    fecha_imagen DATE NOT NULL,
    ndvi_promedio DECIMAL(5, 4),
    ndvi_min DECIMAL(5, 4),
    ndvi_max DECIMAL(5, 4),
    ndvi_desviacion DECIMAL(5, 4),
    construcciones_detectadas BOOLEAN DEFAULT FALSE,
    porcentaje_recuperacion DECIMAL(5, 2),
    calidad_imagen VARCHAR(20) CHECK (calidad_imagen IN ('excelente', 'buena', 'regular', 'mala')),
    nubosidad_porcentaje DECIMAL(5, 2),
    notas TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(incendio_id, mes_numero)
);

-- Tabla de superposiciones entre incendios
CREATE TABLE superposiciones (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    incendio_a_id UUID NOT NULL REFERENCES incendios(id) ON DELETE CASCADE,
    incendio_b_id UUID NOT NULL REFERENCES incendios(id) ON DELETE CASCADE,
    porcentaje_superposicion DECIMAL(5, 2) NOT NULL,
    area_superpuesta_hectareas DECIMAL(10, 2),
    dias_transcurridos INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CHECK (incendio_a_id < incendio_b_id), -- Evita duplicados A-B y B-A
    UNIQUE(incendio_a_id, incendio_b_id)
);

-- Índices para optimizar consultas espaciales
CREATE INDEX idx_incendios_geometria ON incendios USING GIST(geometria);
CREATE INDEX idx_incendios_fecha ON incendios(fecha_deteccion);
CREATE INDEX idx_incendios_provincia ON incendios(provincia);
CREATE INDEX idx_incendios_tipo ON incendios(tipo);
CREATE INDEX idx_incendios_estado ON incendios(estado_analisis);

-- Índices para análisis temporal
CREATE INDEX idx_analisis_incendio ON analisis_mensual(incendio_id);
CREATE INDEX idx_analisis_mes ON analisis_mensual(mes_numero);
CREATE INDEX idx_analisis_fecha ON analisis_mensual(fecha_imagen);

-- Índices para superposiciones
CREATE INDEX idx_superposiciones_a ON superposiciones(incendio_a_id);
CREATE INDEX idx_superposiciones_b ON superposiciones(incendio_b_id);

-- Función para actualizar updated_at automáticamente
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger para actualizar updated_at en incendios
CREATE TRIGGER update_incendios_updated_at
    BEFORE UPDATE ON incendios
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Función para detectar incendios recurrentes automáticamente
CREATE OR REPLACE FUNCTION detectar_incendio_recurrente()
RETURNS TRIGGER AS $$
DECLARE
    incendio_anterior UUID;
    dias_diferencia INTEGER;
BEGIN
    -- Buscar incendios previos a menos de 100m (solo si es nuevo)
    IF NEW.tipo = 'nuevo' THEN
        SELECT i.id, (NEW.fecha_deteccion - i.fecha_deteccion) INTO incendio_anterior, dias_diferencia
        FROM incendios i
        WHERE i.id != NEW.id
          AND ST_DWithin(
              i.geometria::geography,
              NEW.geometria::geography,
              100  -- 100 metros
          )
          AND i.fecha_deteccion < NEW.fecha_deteccion
          AND (NEW.fecha_deteccion - i.fecha_deteccion) >= 180  -- 6 meses = ~180 días
        ORDER BY i.fecha_deteccion DESC
        LIMIT 1;

        -- Si encontró incendio previo, marcar como recurrente
        IF incendio_anterior IS NOT NULL THEN
            NEW.tipo := 'recurrente';
            NEW.incendio_previo_id := incendio_anterior;
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger para detectar recurrencia al insertar
CREATE TRIGGER trigger_detectar_recurrente
    BEFORE INSERT ON incendios
    FOR EACH ROW
    EXECUTE FUNCTION detectar_incendio_recurrente();

-- Función para detectar superposiciones automáticamente
CREATE OR REPLACE FUNCTION detectar_superposiciones()
RETURNS TRIGGER AS $$
DECLARE
    incendio_record RECORD;
    area_interseccion DECIMAL;
    porcentaje DECIMAL;
    dias_diff INTEGER;
BEGIN
    -- Buscar incendios con superposición > 5%
    FOR incendio_record IN
        SELECT 
            i.id,
            i.fecha_deteccion,
            ST_Area(ST_Intersection(i.geometria::geography, NEW.geometria::geography)) as area_inter,
            ST_Area(i.geometria::geography) as area_i,
            ST_Area(NEW.geometria::geography) as area_new
        FROM incendios i
        WHERE i.id != NEW.id
          AND i.geometria IS NOT NULL
          AND NEW.geometria IS NOT NULL
          AND ST_Intersects(i.geometria, NEW.geometria)
    LOOP
        -- Calcular porcentaje de superposición (respecto al más pequeño)
        area_interseccion := incendio_record.area_inter;
        porcentaje := (area_interseccion / LEAST(incendio_record.area_i, incendio_record.area_new)) * 100;

        -- Solo registrar si superposición >= 5%
        IF porcentaje >= 5 THEN
            dias_diff := ABS(NEW.fecha_deteccion - incendio_record.fecha_deteccion);
            
            -- Insertar en tabla de superposiciones (evitando duplicados)
            INSERT INTO superposiciones (
                incendio_a_id,
                incendio_b_id,
                porcentaje_superposicion,
                area_superpuesta_hectareas,
                dias_transcurridos
            )
            VALUES (
                LEAST(NEW.id, incendio_record.id),
                GREATEST(NEW.id, incendio_record.id),
                porcentaje,
                area_interseccion / 10000,  -- m² a hectáreas
                dias_diff
            )
            ON CONFLICT (incendio_a_id, incendio_b_id) DO NOTHING;
        END IF;
    END LOOP;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger para detectar superposiciones al insertar
CREATE TRIGGER trigger_detectar_superposiciones
    AFTER INSERT ON incendios
    FOR EACH ROW
    EXECUTE FUNCTION detectar_superposiciones();

-- Comentarios para documentación
COMMENT ON TABLE incendios IS 'Registro de incendios forestales detectados en Argentina desde 2015';
COMMENT ON TABLE analisis_mensual IS 'Análisis temporal mensual de recuperación post-incendio (36 meses)';
COMMENT ON TABLE superposiciones IS 'Registro de incendios con áreas superpuestas (>5%)';
COMMENT ON COLUMN incendios.geometria IS 'Polígono del área afectada en WGS84 (EPSG:4326)';
COMMENT ON COLUMN incendios.tipo IS 'Clasificación: nuevo o recurrente (<100m, >6 meses)';
COMMENT ON COLUMN analisis_mensual.ndvi_promedio IS 'Índice de vegetación normalizado promedio (-1 a 1)';