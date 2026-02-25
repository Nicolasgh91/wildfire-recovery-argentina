"""
Recovery Task: Monitoreo de recuperación de vegetación post-incendio.

Analyzes vegetation recovery using VAEService + GEE and persists
results to the vegetation_monitoring table with upsert semantics.
"""

import logging
import time
from datetime import datetime, timedelta, date
from celery import group
from ..celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name='workers.tasks.recovery.analyze_recovery',
    queue='vae',
    max_retries=2,
)
def analyze_recovery(self, fire_event_id, months_after=None):
    """
    Analiza recuperación de vegetación post-incendio usando NDVI.
    Persists results to vegetation_monitoring with upsert.

    Args:
        fire_event_id: UUID del fuego
        months_after: Cuántos meses después analizar (None = auto-detect)
    """
    import time
    from app.db.session import SessionLocal
    from sqlalchemy import text

    logger.info(f"🚀 [RECOVERY] === STARTING RECOVERY ANALYSIS ===")
    logger.info(f"🚀 [RECOVERY] Event ID: {fire_event_id}")
    start_time = time.time()

    db = SessionLocal()
    try:
        logger.info(f"🚀 [RECOVERY] Fetching fire event details...")
        
        # 1. Get fire event geometry
        fire_row = db.execute(
            text("""
                SELECT
                    id,
                    start_date,
                    ST_Y(centroid::geometry) as lat,
                    ST_X(centroid::geometry) as lon,
                    estimated_area_hectares
                FROM fire_events
                WHERE id = :fire_id
            """),
            {"fire_id": str(fire_event_id)},
        ).fetchone()

        if not fire_row:
            logger.warning(f" [RECOVERY]  Fire event {fire_event_id} not found, skipping")
            return {
                'fire_event_id': str(fire_event_id),
                'status': 'skipped',
                'reason': 'not_found'
            }

        # Log event details
        event_id, fire_date, lat, lon, area_ha = fire_row
        logger.info(f" [RECOVERY]  Fire details: date={fire_date}, lat={lat:.4f}, lon={lon:.4f}, area={area_ha}ha")

        # 2. Build bbox
        bbox = {
            'min_lon': lon - 0.01,  # ~1km buffer
            'max_lon': lon + 0.01,
            'min_lat': lat - 0.01,
            'max_lat': lat + 0.01,
        }
        logger.info(f" [RECOVERY]  Bbox: {bbox}")

        # 3. Determine analysis date
        if months_after is None:
            analysis_date = datetime.today()
        else:
            analysis_date = self._add_months(fire_date, months_after)
        
        logger.info(f" [RECOVERY]  Analysis date: {analysis_date} (months_after: {months_after})")

        # 4. Initialize VAE service
        logger.info(f" [RECOVERY]  Initializing VAE service...")
        vae_service = VAEService()

        # 5. Get baseline NDVI
        logger.info(f" [RECOVERY]  Starting baseline NDVI calculation...")
        baseline_start = time.time()
        try:
            baseline_ndvi = vae_service._get_baseline_ndvi(bbox, fire_date)
            baseline_time = time.time() - baseline_start
            logger.info(f" [RECOVERY]  Baseline NDVI: {baseline_ndvi:.4f} (took {baseline_time:.2f}s)")
        except Exception as e:
            logger.error(f" [RECOVERY]  Baseline NDVI failed: {e}")
            raise

        # 6. Get current NDVI (with median optimization)
        logger.info(f" [RECOVERY]  Starting current NDVI calculation (median optimized)...")
        current_start = time.time()
        try:
            current_ndvi = vae_service._get_current_ndvi(bbox, analysis_date)
            current_time = time.time() - current_start
            logger.info(f" [RECOVERY]  Current NDVI: {current_ndvi:.4f} (took {current_time:.2f}s)")
        except Exception as e:
            logger.error(f" [RECOVERY]  Current NDVI failed: {e}")
            raise

        # 7. Calculate recovery metrics
        logger.info(f" [RECOVERY]  Calculating recovery metrics...")
        ndvi_change = current_ndvi - baseline_ndvi
        recovery_pct = max(0, min(100, (current_ndvi / baseline_ndvi) * 100)) if baseline_ndvi > 0 else 0
        
        logger.info(f" [RECOVERY]  Results: NDVI change={ndvi_change:+.4f}, Recovery={recovery_pct:.1f}%")

        # 8. Classify recovery status
        recovery_status = vae_service._classify_recovery_status(recovery_pct)
        logger.info(f" [RECOVERY]  Recovery status: {recovery_status.value}")

        # 9. Detect human activity
        human_activity_detected = recovery_pct > vae_service._get_expected_recovery(months_after) * 1.2
        activity_type = 'rapid_greening' if human_activity_detected else 'natural_recovery'
        
        logger.info(f" [RECOVERY]  Human activity: {human_activity_detected}, Type: {activity_type}")

        # 10. Persist results
        logger.info(f" [RECOVERY]  Persisting to database...")
        persist_start = time.time()
        
        upsert_query = text("""
            INSERT INTO vegetation_monitoring (
                fire_event_id, monitoring_date, ndvi_mean, baseline_ndvi,
                recovery_percentage, human_activity_detected, activity_type
            ) VALUES (
                :fire_event_id, :monitoring_date, :ndvi_mean, :baseline_ndvi,
                :recovery_percentage, :human_activity_detected, :activity_type
            )
            ON CONFLICT (fire_event_id, monitoring_date) DO UPDATE SET
                ndvi_mean = EXCLUDED.ndvi_mean,
                ndvi_min = EXCLUDED.ndvi_min,
                ndvi_max = EXCLUDED.ndvi_max,
                baseline_ndvi = EXCLUDED.baseline_ndvi,
                recovery_percentage = EXCLUDED.recovery_percentage,
                human_activity_detected = EXCLUDED.human_activity_detected,
                activity_type = EXCLUDED.activity_type,
                classification_confidence = EXCLUDED.classification_confidence,
                updated_at = NOW()
        """)

        db.execute(upsert_query, {
            "fire_event_id": str(fire_event_id),
            "monitoring_date": monitoring_date,
            "months_after_fire": analysis.months_after_fire,
            "ndvi_mean": analysis.current_ndvi,
            "ndvi_min": None,
            "ndvi_max": None,
            "baseline_ndvi": analysis.baseline_ndvi,
            "recovery_percentage": analysis.recovery_percentage,
            "human_activity_detected": analysis.anomaly_detected,
            "activity_type": analysis.anomaly_type.value if analysis.anomaly_detected else None,
            "classification_confidence": analysis.anomaly_confidence if analysis.anomaly_detected else None,
        })
        db.commit()

        logger.info(
            f"Recovery analysis persisted for {fire_event_id}: "
            f"{analysis.recovery_percentage:.1f}% recovered"
        )
        return {
            "fire_event_id": str(fire_event_id),
            "status": "completed",
            "recovery_percentage": analysis.recovery_percentage,
            "ndvi_change": analysis.ndvi_change,
            "recovery_status": analysis.recovery_status.value,
            "months_after_fire": analysis.months_after_fire,
            "analysis_date": monitoring_date.isoformat(),
        }

    except Exception as exc:
        db.rollback()
        logger.error(f"Error analyzing recovery for {fire_event_id}: {exc}")
        raise self.retry(exc=exc, countdown=300)
    finally:
        db.close()


@celery_app.task(
    bind=True,
    name='workers.tasks.recovery.batch_recovery_analysis',
    queue='vae',
    max_retries=2,
)
def batch_recovery_analysis(self, fire_event_ids=None, max_events=50, months_list=None):
    """
    Ejecuta análisis de recuperación para eventos activos.

    Cuando fire_event_ids es None o vacío, consulta la BD para obtener
    los eventos activos más recientes (< 36 meses). Limita a max_events
    por ejecución para proteger la cuota GEE.

    Programada mensualmente vía Celery Beat.

    Args:
        fire_event_ids: Lista de UUIDs (opcional; si vacía, auto-query)
        max_events: Máximo de eventos a procesar por batch
        months_list: Not used (auto-detected per event), kept for compatibility
    """
    from app.db.session import SessionLocal
    from sqlalchemy import text

    try:
        # If no IDs provided, query DB for active events
        if not fire_event_ids:
            db = SessionLocal()
            try:
                rows = db.execute(text("""
                    SELECT fe.id
                    FROM fire_events fe
                    WHERE fe.start_date > NOW() - INTERVAL '36 months'
                      AND fe.status IN ('active', 'monitoring', 'contained')
                      AND fe.centroid IS NOT NULL
                    ORDER BY fe.start_date DESC
                    LIMIT :max_events
                """), {"max_events": max_events}).fetchall()
                fire_event_ids = [str(row.id) for row in rows]
            finally:
                db.close()

        logger.info(f"Batch recovery analysis: {len(fire_event_ids)} fires...")

        signatures = [
            analyze_recovery.s(fire_id).set(queue='vae')
            for fire_id in fire_event_ids
        ]

        group_result = group(signatures).apply_async() if signatures else None

        return {
            'total_tasks_enqueued': len(signatures),
            'fire_events': len(fire_event_ids),
            'status': 'queued',
            'group_id': group_result.id if group_result else None,
        }

    except Exception as exc:
        logger.error(f"Error in batch recovery analysis: {exc}")
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(
    bind=True,
    name='workers.tasks.recovery.analyze_episode_recovery',
    queue='vae',
    max_retries=2,
)
def analyze_episode_recovery(self, episode_id, months_after=None):
    """
    Analiza recuperación de vegetación para un episodio completo.
    
    Selecciona el evento representativo del episodio (más reciente o mayor FRP)
    y ejecuta el análisis de recuperación sobre ese evento.
    
    Args:
        episode_id: UUID del episodio
        months_after: Cuántos meses después analizar (None = auto-detect)
    """
    from app.db.session import SessionLocal
    from sqlalchemy import text
    
    db = SessionLocal()
    try:
        logger.info(f"Analyzing episode recovery for episode {episode_id}...")
        
        # 1. Get representative event from episode
        event_row = db.execute(text("""
            SELECT fe.id, fe.start_date, 
                   ST_Y(fe.centroid::geometry) as lat,
                   ST_X(fe.centroid::geometry) as lon,
                   fe.estimated_area_hectares,
                   fe.avg_frp, fe.max_frp
            FROM fire_events fe
            JOIN fire_episode_events fee ON fe.id = fee.event_id
            WHERE fee.episode_id = :episode_id
            AND fe.centroid IS NOT NULL
            ORDER BY fe.max_frp DESC, fe.start_date DESC
            LIMIT 1
        """), {"episode_id": str(episode_id)}).fetchone()
        
        if not event_row:
            logger.warning(f"No representative event found for episode {episode_id}")
            return {
                'episode_id': str(episode_id),
                'status': 'skipped',
                'reason': 'no_representative_event'
            }
        
        representative_event_id = event_row[0]
        logger.info(f"Selected representative event {representative_event_id} for episode {episode_id}")
        
        # 2. Execute recovery analysis on representative event
        from .recovery import analyze_recovery
        result = analyze_recovery.delay(representative_event_id, months_after)
        
        # 3. Store episode-level recovery status (optional enhancement)
        # This could be added later to cache recovery status at episode level
        
        return {
            'episode_id': str(episode_id),
            'representative_event_id': str(representative_event_id),
            'recovery_task_id': result.id,
            'status': 'queued',
            'event_frp': float(event_row[5]) if event_row[5] else None,
        }
        
    except Exception as exc:
        logger.error(f"Error analyzing episode recovery for {episode_id}: {exc}")
        raise self.retry(exc=exc, countdown=60)
    finally:
        db.close()


@celery_app.task(
    bind=True,
    name='workers.tasks.recovery.batch_episode_recovery_analysis',
    queue='vae',
    max_retries=2,
)
def batch_episode_recovery_analysis(self, max_episodes=50, recent_only=False, carousel_only=False):
    """
    Enhanced batch processing with comprehensive monitoring and logging.
    """
    import time
    import logging
    import subprocess
    from datetime import datetime
    from app.db.session import SessionLocal
    from sqlalchemy import text
    
    logger = logging.getLogger(__name__)
    
    # Initialize monitoring
    start_time = time.time()
    batch_start = datetime.now()
    episodes_processed = 0
    episodes_failed = 0
    gee_requests_start = _get_current_gee_requests()
    
    logger.info(f"🚀 [BACKFILL] === STARTING HISTORICAL BACKFILL ===")
    logger.info(f"🚀 [BACKFILL] Task ID: {self.request.id}")
    logger.info(f"🚀 [BACKFILL] Parameters: max_episodes={max_episodes}, recent_only={recent_only}, carousel_only={carousel_only}")
    logger.info(f"🚀 [BACKFILL] Start time: {batch_start}")
    
    db = SessionLocal()
    try:
        # Build query based on parameters
        where_conditions = ["fe.centroid IS NOT NULL"]
        if recent_only:
            where_conditions.append("fe.start_date >= NOW() - INTERVAL '12 months'")
        if carousel_only:
            where_conditions.append("ep.status IN ('active', 'monitoring')")
        
        where_clause = " AND ".join(where_conditions)
        
        # Get episodes for processing
        episodes_query = text(f"""
            SELECT ep.id, ep.status, ep.created_at,
                   COUNT(fe.id) as event_count,
                   MAX(fe.start_date) as latest_fire_date,
                   ST_Y(ep.centroid::geometry) as lat,
                   ST_X(ep.centroid::geometry) as lon,
                   CASE WHEN ep.status = 'active' THEN 1
                        WHEN ep.status = 'monitoring' THEN 2
                        ELSE 3 END as status_priority
            FROM fire_episodes ep
            JOIN fire_episode_events fee ON ep.id = fee.episode_id
            JOIN fire_events fe ON fee.event_id = fe.id
            WHERE {where_clause}
            GROUP BY ep.id, ep.status, ep.created_at, ep.centroid
            ORDER BY status_priority, ep.created_at DESC
            LIMIT :max_episodes
        """)
        
        episodes = db.execute(episodes_query, {"max_episodes": max_episodes}).fetchall()
        
        total_episodes = len(episodes)
        logger.info(f"🚀 [BACKFILL] Found {total_episodes} episodes to process")
        
        if total_episodes == 0:
            logger.info(f"🚀 [BACKFILL] No episodes found for processing")
            return {
                'task_id': self.request.id,
                'episodes_found': 0,
                'episodes_processed': 0,
                'status': 'completed',
                'message': 'No episodes found'
            }
        
        # Process episodes with progress tracking
        logger.info(f"🚀 [BACKFILL] Starting episode processing...")
        
        for i, episode_row in enumerate(episodes, 1):
            episode_id = str(episode_row[0])
            
            # Progress logging every 10 episodes
            if i % 10 == 0 or i == total_episodes:
                progress_pct = (i / total_episodes) * 100
                elapsed = time.time() - start_time
                avg_time_per_episode = elapsed / i
                remaining_episodes = total_episodes - i
                eta_seconds = remaining_episodes * avg_time_per_episode
                eta_minutes = eta_seconds / 60
                
                current_gee_requests = _get_current_gee_requests()
                requests_used = current_gee_requests - gee_requests_start
                
                logger.info(f"🚀 [BACKFILL] 📊 Progress: {i}/{total_episodes} ({progress_pct:.1f}%)")
                logger.info(f"🚀 [BACKFILL] ⏱️  Elapsed: {elapsed/60:.1f}min, ETA: {eta_minutes:.1f}min")
                logger.info(f"🚀 [BACKFILL] 📡 GEE requests used: {requests_used}")
                logger.info(f"🚀 [BACKFILL] ✅ Success: {episodes_processed}, ❌ Failed: {episodes_failed}")
            
            try:
                # Process individual episode
                logger.info(f"🚀 [BACKFILL] Processing episode {i}/{total_episodes}: {episode_id}")
                
                episode_start = time.time()
                result = analyze_episode_recovery.apply_async(args=[episode_id])
                
                # Wait for completion (sync for monitoring)
                episode_result = result.get(timeout=300)  # 5 minute timeout
                episode_time = time.time() - episode_start
                
                episodes_processed += 1
                
                logger.info(f"🚀 [BACKFILL] ✅ Episode {episode_id} completed in {episode_time:.2f}s: {episode_result.get('status', 'unknown')}")
                
            except Exception as e:
                episodes_failed += 1
                logger.error(f"🚀 [BACKFILL] ❌ Episode {episode_id} failed: {e}")
                
                # Continue processing other episodes
                continue
        
        # Final statistics
        total_time = time.time() - start_time
        final_gee_requests = _get_current_gee_requests()
        total_requests = final_gee_requests - gee_requests_start
        
        logger.info(f"🚀 [BACKFILL] 🎉 === BACKFILL COMPLETED ===")
        logger.info(f"🚀 [BACKFILL] 📊 Final Results:")
        logger.info(f"🚀 [BACKFILL]    Episodes processed: {episodes_processed}/{total_episodes}")
        logger.info(f"🚀 [BACKFILL]    Episodes failed: {episodes_failed}")
        logger.info(f"🚀 [BACKFILL]    Success rate: {(episodes_processed/total_episodes)*100:.1f}%")
        logger.info(f"🚀 [BACKFILL]    Total time: {total_time/60:.1f} minutes")
        logger.info(f"🚀 [BACKFILL]    Avg time per episode: {total_time/total_episodes:.2f}s")
        logger.info(f"🚀 [BACKFILL]    GEE requests used: {total_requests}")
        logger.info(f"🚀 [BACKFILL]    Avg requests per episode: {total_requests/total_episodes:.1f}")
        
        return {
            'task_id': self.request.id,
            'episodes_found': total_episodes,
            'episodes_processed': episodes_processed,
            'episodes_failed': episodes_failed,
            'success_rate': (episodes_processed/total_episodes)*100,
            'total_time_minutes': total_time/60,
            'gee_requests_used': total_requests,
            'status': 'completed'
        }
        
    except Exception as exc:
        total_time = time.time() - start_time
        logger.error(f"🚀 [BACKFILL] ❌ Backfill failed after {total_time/60:.1f} minutes: {exc}")
        raise self.retry(exc=exc, countdown=60)
    finally:
        db.close()

def _get_current_gee_requests():
    """Get current GEE request count from worker logs."""
    try:
        result = subprocess.run(
            ["docker", "logs", "forestguard-worker-vae", "--tail", "50"],
            capture_output=True, text=True, timeout=10
        )
        
        lines = result.stdout.split('\n')
        for line in reversed(lines):
            if "GEE requests hoy:" in line:
                return int(line.split(':')[-1].strip())
        
        return 0
    except:
        return 0
