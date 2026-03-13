# Análisis de impacto en quota GEE: scheduling y backfill VAE

Fecha: 2026-03-12
Contexto: GEE free tier — 50 000 req/día, 40 concurrentes, rate limit actual 1 req/s.

---

## Pregunta 7: scheduling — ¿qué combinación activar?

### Consumo por task

Cada ejecución de `analyze_recovery` consume **2 requests GEE** (1 baseline + 1 current NDVI).
Cada ejecución de `detect_destruction` consume **2-3 requests GEE** (baseline + current + opcional land-use comparison).

Para simplificar: **~4 req GEE por evento** cuando ambos tasks se ejecutan (recovery + destruction).

### Escenarios de scheduling

Se asumen **200 eventos activos** (eventos con incendio en los últimos 36 meses que requieren monitoreo).

| Escenario | Frecuencia | Eventos procesados/ciclo | Req GEE/ciclo | Req GEE/día | % quota diaria | Req GEE/mes | Riesgo |
|---|---|---|---|---|---|---|---|
| **A) Solo monthly** | 1×/mes | 200 | 800 | ~27/día (distribuido en 30 días) | 0.05% | 800 | Mínimo |
| **B) Monthly + weekly-recent** | monthly (todos) + weekly (eventos < 6 meses) | 200 + ~50×4 | 800 + 800 | ~53/día | 0.1% | 1 600 | Bajo |
| **C) Monthly + weekly-recent + episodios** | B + episode aggregation semanal | 200 + 200 + ~30 episodios | 800 + 800 + 120 | ~57/día | 0.11% | 1 720 | Bajo |
| **D) Todos + carrusel + reportes** | C + tareas carrusel/HD que comparten GEE | C + ~500 req carrusel/día | C + 500 | ~557/día | 1.1% | ~17 000 | Moderado |

### Observaciones

- **Monthly solo (A)** es extremadamente conservador. Genera datos suficientes para el gráfico NDVI temporal pero con granularidad mensual.
- **Monthly + weekly-recent (B)** agrega valor real: los eventos recientes (< 6 meses) son los más dinámicos y donde la detección temprana de cambio de uso importa bajo ley 26.815. El costo adicional es despreciable.
- La quota GEE no es el cuello de botella en ningún escenario razonable de scheduling. El riesgo real es la **concurrencia**: con 1 req/s y worker-gee con concurrency=1, procesar 200 eventos toma ~800 segundos (~13 minutos). Aceptable para un batch nocturno.
- El peligro no está en el scheduling periódico sino en los **endpoints HTTP que llaman GEE en tiempo real** (37 req/request de timeline). Eso sí consume quota rápidamente.

### Recomendación

**Activar escenario B (monthly + weekly-recent)** como configuración de producción.

---

## Pregunta 8: backfill de episodios históricos

### Estimación de volumen

Para calcular el impacto, necesitamos estimar cuántos eventos/episodios necesitan backfill. Escenarios según volumen:

| Volumen | Eventos sin datos VAE | Req GEE total (×4/evento) | Tiempo a 1 req/s | Días a 10 000 req/día | % quota día completo |
|---|---|---|---|---|---|
| **Bajo: < 50** | 50 | 200 | ~3 min | < 1 día | 0.4% |
| **Medio: 50-200** | 200 | 800 | ~13 min | < 1 día | 1.6% |
| **Alto: 200-500** | 500 | 2 000 | ~33 min | < 1 día | 4% |
| **Muy alto: > 500** | 1 000 | 4 000 | ~67 min | < 1 día | 8% |

### Backfill con serie temporal completa (36 meses)

Si además de calcular el estado actual se quiere generar la serie histórica completa (un registro NDVI por mes desde la fecha del incendio), el costo se multiplica:

| Volumen | Eventos | Meses promedio de historia | Req GEE total | Tiempo a 1 req/s | Días necesarios (cap 10 000/día) |
|---|---|---|---|---|---|
| **Bajo** | 50 | 12 | 1 200 | ~20 min | < 1 día |
| **Medio** | 200 | 18 | 7 200 | ~2 h | < 1 día |
| **Alto** | 500 | 24 | 24 000 | ~6.7 h | 2-3 días |
| **Muy alto** | 1 000 | 24 | 48 000 | ~13.3 h | 5 días |

### Estrategias de backfill

| Estrategia | Descripción | Req GEE/día | Días para 500 eventos | Ventaja | Desventaja |
|---|---|---|---|---|---|
| **Agresivo** | Procesar todo en 1-2 noches, cap 25 000 req/día | 25 000 | 1 día (solo actual) / 1-2 días (con serie) | Rápido | Compite con carrusel y scheduling regular |
| **Moderado** | 5 000 req/día dedicados a backfill | 5 000 | 1 día (actual) / 5 días (con serie) | No impacta operación diaria | Más lento |
| **Conservador** | 50 eventos/noche, solo estado actual | ~200 | 10 noches | Riesgo cero de agotar quota | 2 semanas para completar |
| **Priorizado** | Solo eventos en áreas protegidas o con sospecha de cambio de uso primero | Variable | Variable | Máximo valor legal por req GEE | Requiere query de priorización |

### Recomendación

**Estrategia priorizada + moderada:** primero eventos en áreas protegidas (relevancia legal bajo ley 26.815), luego el resto. Cap diario de 5 000 req GEE para backfill, ejecutado en horario de baja actividad (madrugada UTC-3).

---

## Resumen de decisiones pendientes

| # | Pregunta | Escenarios | Impacto quota | Mi recomendación |
|---|---|---|---|---|
| 7 | ¿Qué schedules activar? | A (solo monthly) / B (+ weekly-recent) / C (+ episodios) | 0.05% a 0.11% diario | **B** — monthly + weekly-recent |
| 8 | ¿Hacer backfill histórico? | Sin backfill / solo actual / con serie completa | 0% a 8% según volumen | **Verificar volumen en BD** y aplicar estrategia priorizada |
| 9 | ¿Endpoints con JWT o públicos? | Todo JWT / lectura pública / mixto | No aplica a quota GEE | (pendiente de respuesta) |
| 10 | ¿Endpoint trigger manual? | Sí con rate limit / no / deshabilitado | 4 req/trigger (bajo) pero riesgo de abuso | (pendiente de respuesta) |

---

## Actualización (2026-03-12): estrategia de backfill refinada

La decisión final usa dos regímenes con fecha de corte **2025-12-01**:

- **Régimen A** (históricos cerrados pre-dic 2025): puntos semestrales → ~2 400 req GEE
- **Régimen B** (recientes cerrados dic 2025+): puntos mensuales → ~640 req GEE
- **Total backfill one-shot:** ~3 040 req GEE
- Solo episodios cerrados (`extinct`, `closed`). Episodios activos cubiertos por scheduling regular.
- El análisis mensual se mantendrá para todos los episodios nuevos que surjan a partir de 2026, una vez que pasen a estado cerrado.

Esto reemplaza la estimación anterior de "serie completa semestral" uniforme.
