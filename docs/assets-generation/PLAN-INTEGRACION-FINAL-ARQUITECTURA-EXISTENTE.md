# 🎯 PLAN DE INTEGRACIÓN: HD/PDF/Thumbnails (Arquitectura Existente)

**Basado en:** status_2026-02-22.md  
**Objetivo:** Unificar paso 3 (HD/PDF) + Carrusel manteniendo código existente  
**Tiempo:** 3-4 horas de implementación  
**Riesgo:** Bajo (no modifica APIs existentes, solo las extiende)

---

## 📍 SITUACIÓN ACTUAL

### Flujos que YA existen:

**Flujo 1: Exploraciones HD** (paso 3, parte A)
```
POST /api/v1/explorations/{id}/generate
  ↓
Celery: generate_exploration_hd.delay(...)
  ↓
Worker: run_generation_job() → genera assets HD
  ↓
GET /api/v1/explorations/{id}/assets → retorna URLs firmadas
```

**Flujo 2: Reports/PDF judicial** (paso 3, parte B - SEPARADO)
```
POST /api/v1/reports/judicial
  ↓
genera PDF independiente
```

**Flujo 3: Carrusel/Thumbnails**
```
Task programada: generate_carousel()
  ↓
ImageryService.run_carousel()
  ↓
actualiza fire_episodes.slides_data
  ↓
Frontend consume slides_data via /fire-episodes?mode=active
```

---

## 🔴 PROBLEMA

**Paso 3 tiene dos pipelines desconectados:**
- HD se genera en `/explorations/.../generate`
- PDF se genera en `/reports/judicial` (independiente)
- Resultado: usuario genera HD, luego tiene que generar PDF por separado

**Solución:** Unificar en UN SOLO endpoint que haga HD + PDF en paralelo

---

## ✅ SOLUCIÓN PROPUESTA

### Opción A: Mínima (sin cambiar APIs existentes)

**Mantener ambos endpoints pero:**
1. Mejorar `run_generation_job()` para generar PDF automáticamente tras HD
2. Retornar PDF URL junto con HD URLs en `GET .../assets`

**Ventaja:** Sin cambios en APIs
**Desventaja:** Dos endpoints separados aún existe en UI

### Opción B: Elegante (unificar en endpoint único)

**Crear nuevo endpoint unificado:**
```
POST /api/v1/explorations/{id}/generate-complete
  ↓
Genera HD + PDF en paralelo
  ↓
GET /api/v1/explorations/{id}/assets → retorna todo
```

**Ventaja:** Una sola llamada, UX limpia
**Desventaja:** Nuevo endpoint (pero Opción A sigue funcionando)

---

## 🏗️ ARQUITECTURA DE SOLUCIÓN (Opción A + B)

### PASO 1: Extender `run_generation_job()` para incluir PDF

**Archivo:** `app/workers/exploration_hd_worker.py`

Cambios mínimos:

```python
# En run_generation_job(), después de generar HD:

def run_generation_job(job_id: str):
    """Genera HD + PDF en UN SOLO job"""
    
    # ... código existente de HD ...
    
    # NEW: Generar PDF automáticamente tras HD
    try:
        pdf_path = generate_pdf_from_hd_results(
            job_id=job_id,
            investigation_id=investigation_id,
            hd_results=job.results  # reutilizar resultados HD
        )
        
        # Agregar PDF al resultado
        job.results['pdf_path'] = pdf_path
        db.commit()
        
        logger.info(f"✅ PDF generado para job {job_id}")
    except Exception as e:
        logger.error(f"⚠️ PDF generation failed: {e}")
        # NO fallar el job, solo loguear
```

### PASO 2: Nueva función para generar PDF desde resultados HD

**Archivo:** `app/workers/exploration_hd_worker.py` (agregar función)

```python
def generate_pdf_from_hd_results(
    job_id: str,
    investigation_id: str,
    hd_results: dict
) -> str:
    """
    Genera PDF usando imágenes/datos del job HD.
    Retorna ruta local del PDF para upload a OCI.
    """
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    from datetime import datetime
    
    try:
        pdf_path = f"/tmp/exploration_{investigation_id}_{job_id}.pdf"
        pdf = canvas.Canvas(pdf_path, pagesize=letter)
        
        # Header
        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawString(50, 750, f"Reporte de Exploración Satelital")
        
        # Metadatos
        pdf.setFont("Helvetica", 10)
        y = 720
        
        pdf.drawString(50, y, f"ID Investigación: {investigation_id}")
        y -= 15
        pdf.drawString(50, y, f"Job ID: {job_id}")
        y -= 15
        pdf.drawString(50, y, f"Fecha: {datetime.utcnow().isoformat()}")
        y -= 30
        
        # Agregar imágenes del resultado HD
        if 'images' in hd_results:
            y = 600
            for idx, img_info in enumerate(hd_results['images'][:3]):  # Máx 3 imágenes
                if 'local_path' in img_info:
                    try:
                        from reportlab.platypus import Image as RLImage
                        pdf.drawString(50, y, f"Imagen {idx + 1}: {img_info.get('band', 'Unknown')}")
                        y -= 20
                        # Insertar miniatura
                        if os.path.exists(img_info['local_path']):
                            pdf.drawImage(
                                img_info['local_path'],
                                50, y - 200,
                                width=300,
                                height=200
                            )
                            y -= 220
                    except Exception as e:
                        logger.warning(f"Could not embed image: {e}")
        
        # Resumen
        y = 150
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(50, y, "Resumen de Resultados")
        y -= 20
        
        pdf.setFont("Helvetica", 10)
        pdf.drawString(50, y, f"Total de imágenes generadas: {len(hd_results.get('images', []))}")
        y -= 15
        pdf.drawString(50, y, f"Estado: {hd_results.get('status', 'unknown')}")
        y -= 15
        
        pdf.save()
        logger.info(f"PDF creado: {pdf_path}")
        
        return pdf_path
        
    except Exception as e:
        logger.error(f"Error generando PDF: {e}")
        raise
```

### PASO 3: Subir PDF a OCI Storage

**Archivo:** `app/workers/exploration_hd_worker.py` (en `run_generation_job()`, tras generar PDF)

```python
def run_generation_job(job_id: str):
    # ... código existente ...
    
    # Después de generar PDF:
    if job.results.get('pdf_path'):
        try:
            from oci_storage_service import oci_storage
            
            with open(job.results['pdf_path'], 'rb') as f:
                pdf_bytes = f.read()
            
            pdf_url = oci_storage.upload_file(
                bucket_name='forestguard-reports',
                object_name=f'explorations/{investigation_id}/{job_id}.pdf',
                file_bytes=pdf_bytes
            )
            
            # Actualizar resultado con URL
            job.results['pdf_url'] = pdf_url
            db.commit()
            
            logger.info(f"✅ PDF subido a OCI: {pdf_url}")
            
            # Limpiar archivo temporal
            os.remove(job.results['pdf_path'])
            
        except Exception as e:
            logger.error(f"Error uploadding PDF: {e}")
```

### PASO 4: Retornar PDF URL en endpoint de assets

**Archivo:** `app/api/v1/explorations.py` (en `get_exploration_assets()`)

```python
@router.get("/explorations/{investigation_id}/assets")
async def get_exploration_assets(investigation_id: str, db: Session = Depends(get_db)):
    """
    Retorna URLs de todos los assets generados (HD + PDF).
    """
    
    job = db.query(ExplorationGenerationJob).filter(
        ExplorationGenerationJob.investigation_id == investigation_id
    ).order_by(ExplorationGenerationJob.created_at.desc()).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="No assets found")
    
    response = {
        'job_id': str(job.id),
        'status': job.status,
        'created_at': job.created_at.isoformat(),
        'assets': {
            'hd_images': job.results.get('hd_images', []),
            'pdf_url': job.results.get('pdf_url'),  # ← NEW
            'all_urls': job.results.get('signed_urls', [])
        }
    }
    
    return response
```

### PASO 5: Frontend - Mostrar PDF en paso 3

**Archivo:** `frontend/src/pages/Exploration.tsx` (en UI de paso 3)

```tsx
// En sección de assets, agregar botón PDF:

{assets?.assets?.pdf_url && (
  <div className="pdf-download">
    <button 
      onClick={() => window.open(assets.assets.pdf_url)}
      className="btn-primary"
    >
      📥 Descargar PDF del Reporte
    </button>
    <p className="text-sm text-gray-500">
      PDF generado automáticamente con análisis e imágenes
    </p>
  </div>
)}
```

### PASO 6 (OPCIONAL): Nuevo endpoint unificado

Si quieres un endpoint único "bonito" (Opción B):

**Archivo:** `app/api/v1/explorations.py` (agregar nuevo endpoint)

```python
@router.post("/explorations/{investigation_id}/generate-complete")
async def generate_exploration_complete(
    investigation_id: str,
    db: Session = Depends(get_db)
):
    """
    Genera exploración COMPLETA (HD + PDF en un solo job).
    Internamente reutiliza generate_exploration_hd con mejoras.
    """
    
    # Validaciones
    investigation = db.query(Investigation).filter(
        Investigation.id == investigation_id
    ).first()
    
    if not investigation:
        raise HTTPException(status_code=404, detail="Investigation not found")
    
    # Crear job (mismo código que endpoint anterior)
    job = ExplorationGenerationJob(
        investigation_id=investigation_id,
        status='pending'
    )
    db.add(job)
    db.commit()
    
    # Encolar con Celery (mismo task, pero generará PDF automáticamente)
    from workers.tasks.exploration_hd_task import generate_exploration_hd
    generate_exploration_hd.delay(job.id)
    
    return {
        'job_id': str(job.id),
        'status': 'pending',
        'message': 'Generating HD images and PDF report...',
        'estimate_seconds': 60  # tiempo estimado
    }
```

---

## 📋 CHECKLIST DE IMPLEMENTACIÓN

### Fase 1: Backend (1.5 horas)
- [ ] Agregar `generate_pdf_from_hd_results()` en `exploration_hd_worker.py`
- [ ] Extender `run_generation_job()` para generar + subir PDF
- [ ] Actualizar `get_exploration_assets()` para retornar `pdf_url`
- [ ] Test con `curl`:
  ```bash
  curl -X POST http://localhost:8000/api/v1/explorations/{id}/generate
  sleep 30
  curl http://localhost:8000/api/v1/explorations/{id}/assets
  # Verificar que retorna pdf_url
  ```

### Fase 2: Frontend (1 hora)
- [ ] Agregar botón "Descargar PDF" en Exploration.tsx paso 3
- [ ] Test en navegador
- [ ] Verificar que PDF se abre en nueva pestaña

### Fase 3: Carrusel (mejorar visibilidad)
- [ ] Verificar que `ImageryService.run_carousel()` actualiza `slides_data`
- [ ] Si `slides_data` sigue vacío, debuggear `ImageryService.refresh_fire()`
- [ ] Agregar logs para ver qué URLs se guardan

### Fase 4: Validación E2E (30 min)
- [ ] Ejecutar exploración completa
- [ ] Generar HD
- [ ] Descargar PDF resultante
- [ ] Verificar carrusel muestra thumbnails

---

## 🎯 IMPACTO MINIMAL

✅ **No cambia:**
- APIs existentes (`/explorations/.../generate` sigue igual)
- Modelos de BD
- Frontend principal (solo se agrega botón)
- Endpoint `/reports/judicial` (sigue disponible)

✅ **Agrega:**
- PDF automático en mismo job que HD
- Botón en UI para descargar PDF
- (Opcional) Nuevo endpoint unificado

✅ **Beneficio:**
- Usuario genera HD → automáticamente obtiene PDF también
- Una sola llamada en lugar de dos
- Mejor UX

---

## ⚠️ RIESGOS Y MITIGACIONES

| Riesgo | Causa | Mitigación |
|--------|-------|-----------|
| PDF generation falla | Error en ReportLab | Try/catch, loguear, NO fallar el job |
| PDF muy grande | Muchas imágenes | Limitar a primeras 3 imágenes |
| OCI upload falla | Network, permiso | Retry, fallback local path |
| Duplicar trabajo | Si existe `/reports/judicial` | Mantener ambos (compatible) |

---

## 🚀 PRÓXIMOS PASOS

1. ¿Quieres Opción A (mínima, mejorar existente) u Opción B (nuevo endpoint)?
2. ¿Tengo acceso al repo para editar directamente o prefieres los cambios en pseudo-código?
3. ¿Quieres que también debugguee por qué `slides_data` está vacío en carrusel?

---

**Recomendación:** 
Implementar **Opción A primero** (extiende lo existente), validar, luego **Opción B como bonus** si quieres UX más limpia.

**Tiempo total:** 2-3 horas con testing.

¿Vamos con esto?
