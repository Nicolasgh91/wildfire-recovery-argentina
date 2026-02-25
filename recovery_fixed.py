"""
Recovery Task: Monitoreo de recuperación de vegetación post-incendio - FIXED VERSION
"""

import logging
import time
import subprocess
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
    """
    from app.db.session import SessionLocal
    from sqlalchemy import text

    logger.info(f"🚀 [RECOVERY] === STARTING RECOVERY ANALYSIS ===")
    logger.info(f"🚀 [RECOVERY] Event ID: {fire_event_id}")
    start_time = time.time()

    db = SessionLocal()
    try:
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
            logger.warning(f"🚀 [RECOVERY] ❌ Fire event {fire_event_id} not found, skipping")
            return {
                'fire_event_id': str(fire_event_id),
                'status': 'skipped',
                'reason': 'not_found'
            }

        event_id, fire_date, lat, lon, area_ha = fire_row
        logger.info(f"🚀 [RECOVERY] 📍 Fire details: date={fire_date}, lat={lat:.4f}, lon={lon:.4f}, area={area_ha}ha")

        # 2. Build bbox
        from app.utils.bbox_utils import create_bbox_from_coordinates
        bbox = create_bbox_from_coordinates(lat, lon)
        logger.info(f"🚀 [RECOVERY] 📍 Bbox: {bbox}")

        # 3. Determine analysis date
        if months_after is None:
            analysis_date = date.today()
        else:
            analysis_date = self._add_months(fire_date, months_after)
        
        logger.info(f"🚀 [RECOVERY] 📅 Analysis date: {analysis_date} (months_after: {months_after})")

        # 4. Initialize VAE service
        logger.info(f"🚀 [RECOVERY] 🔧 Initializing VAE service...")
        from app.services.vae_service import VAEService
        vae_service = VAEService()

        # 5. Get baseline NDVI
        logger.info(f"🚀 [RECOVERY] 📊 Starting baseline NDVI calculation...")
        baseline_start = time.time()
        try:
            baseline_ndvi = vae_service._get_baseline_ndvi(bbox, fire_date)
            baseline_time = time.time() - baseline_start
            logger.info(f"🚀 [RECOVERY] ✅ Baseline NDVI: {baseline_ndvi:.4f} (took {baseline_time:.2f}s)")
        except Exception as e:
            logger.error(f"🚀 [RECOVERY] ❌ Baseline NDVI failed: {e}")
            raise

        # 6. Get current NDVI (with median optimization)
        logger.info(f"🚀 [RECOVERY] 📊 Starting current NDVI calculation (median optimized)...")
        current_start = time.time()
        try:
            current_ndvi = vae_service._get_current_ndvi(bbox, analysis_date)
            current_time = time.time() - current_start
            logger.info(f"🚀 [RECOVERY] ✅ Current NDVI: {current_ndvi:.4f} (took {current_time:.2f}s)")
        except Exception as e:
            logger.error(f"🚀 [RECOVERY] ❌ Current NDVI failed: {e}")
            raise

        # 7. Calculate recovery metrics
        logger.info(f"🚀 [RECOVERY] 📈 Calculating recovery metrics...")
        ndvi_change = current_ndvi - baseline_ndvi
        recovery_pct = max(0, min(100, (current_ndvi / baseline_ndvi) * 100)) if baseline_ndvi > 0 else 0
        
        logger.info(f"🚀 [RECOVERY] 📊 Results: NDVI change={ndvi_change:+.4f}, Recovery={recovery_pct:.1f}%")

        # 8. Classify recovery status
        recovery_status = vae_service._classify_recovery_status(recovery_pct)
        logger.info(f"🚀 [RECOVERY] 🏷️ Recovery status: {recovery_status.value}")

        # 9. Detect human activity
        human_activity_detected = recovery_pct > vae_service._get_expected_recovery(months_after) * 1.2
        activity_type = 'rapid_greening' if human_activity_detected else 'natural_recovery'
        
        logger.info(f"🚀 [RECOVERY] 👥 Human activity: {human_activity_detected}, Type: {activity_type}")

        # 10. Persist results
        logger.info(f"🚀 [RECOVERY] 💾 Persisting to database...")
        persist_start = time.time()
        
        db.execute(text("""
            INSERT INTO vegetation_monitoring (
                fire_event_id, monitoring_date, ndvi_mean, baseline_ndvi,
                recovery_percentage, human_activity_detected, activity_type
            ) VALUES (
                :fire_event_id, :monitoring_date, :ndvi_mean, :baseline_ndvi,
                :recovery_percentage, :human_activity_detected, :activity_type
            )
            ON CONFLICT (fire_event_id, monitoring_date) DO UPDATE SET
                ndvi_mean = EXCLUDED.ndvi_mean,
                baseline_ndvi = EXCLUDED.baseline_ndvi,
                recovery_percentage = EXCLUDED.recovery_percentage,
                human_activity_detected = EXCLUDED.human_activity_detected,
                activity_type = EXCLUDED.activity_type,
                updated_at = NOW()
        """), {
            'fire_event_id': str(event_id),
            'monitoring_date': analysis_date,
            'ndvi_mean': current_ndvi,
            'baseline_ndvi': baseline_ndvi,
            'recovery_percentage': recovery_pct,
            'human_activity_detected': human_activity_detected,
            'activity_type': activity_type,
        })

        db.commit()
        persist_time = time.time() - persist_start
        logger.info(f"🚀 [RECOVERY] ✅ Persisted in {persist_time:.3f}s")

        # 11. Log final results
        total_time = time.time() - start_time
        logger.info(f"🚀 [RECOVERY] 🎉 Recovery analysis persisted for {event_id}: {recovery_pct:.1f}% recovered")
        logger.info(f"🚀 [RECOVERY] ⏱️ Total time: {total_time:.2f}s")
        logger.info(f"🚀 [RECOVERY] === RECOVERY ANALYSIS COMPLETED ===")

        return {
            'fire_event_id': str(event_id),
            'status': 'completed',
            'recovery_percentage': recovery_pct,
            'ndvi_change': ndvi_change,
            'recovery_status': recovery_status.value,
            'months_after_fire': months_after,
            'analysis_date': analysis_date.isoformat(),
            'processing_time': total_time,
        }

    except Exception as exc:
        total_time = time.time() - start_time
        logger.error(f"🚀 [RECOVERY] ❌ Recovery analysis failed after {total_time:.2f}s: {exc}")
        raise self.retry(exc=exc, countdown=60)
    finally:
        db.close()

    def _add_months(self, d: date, months: int) -> date:
        """Suma meses a una fecha."""
        new_month = d.month + months
        new_year = d.year + (new_month - 1) // 12
        new_month = ((new_month - 1) % 12) + 1
        try:
            return date(new_year, new_month, d.day)
        except ValueError:
            return date(new_year, new_month, 28)


@celery_app.task(
    bind=True,
    name='workers.tasks.recovery.analyze_episode_recovery',
    queue='vae',
    max_retries=2,
)
def analyze_episode_recovery(self, episode_id, months_after=None):
    """
    Analiza recuperación para un episodio completo seleccionando el evento representativo.
    """
    from app.db.session import SessionLocal
    from sqlalchemy import text
    
    logger.info(f"🎯 [EPISODE] Analyzing recovery for episode {episode_id}")
    
    db = SessionLocal()
    try:
        # Seleccionar evento representativo (máximo FRP)
        event_row = db.execute(text("""
            SELECT fe.id, fe.start_date, fe.frp, 
                   ST_Y(fe.centroid::geometry) as lat,
                   ST_X(fe.centroid::geometry) as lon
            FROM fire_events fe
            WHERE fe.episode_id = :episode_id
            ORDER BY fe.frp DESC, fe.start_date DESC
            LIMIT 1
        """), {"episode_id": str(episode_id)}).fetchone()
        
        if not event_row:
            logger.warning(f"Episode {episode_id} has no events")
            return {'episode_id': str(episode_id), 'status': 'skipped', 'reason': 'no_events'}
        
        event_id, start_date, frp, lat, lon = event_row
        logger.info(f"🎯 [EPISODE] Selected representative event {event_id} (FRP: {frp})")
        
        # Delegar al análisis de evento individual
        result = analyze_recovery.apply_async(args=[event_id], kwargs={'months_after': months_after})
        
        return {
            'episode_id': str(episode_id),
            'representative_event_id': str(event_id),
            'event_analysis': result.get(),
            'status': 'completed'
        }
        
    except Exception as exc:
        logger.error(f"Episode analysis failed: {exc}")
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
    Enhanced batch processing with comprehensive monitoring and logging - FIXED SQL.
    """
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
    
    from app.db.session import SessionLocal
    from sqlalchemy import text
    
    db = SessionLocal()
    try:
        # Build query based on parameters - FIXED: Use AVG of event centroids
        where_conditions = ["fe.centroid IS NOT NULL"]
        if recent_only:
            where_conditions.append("fe.start_date >= NOW() - INTERVAL '12 months'")
        if carousel_only:
            where_conditions.append("ep.status IN ('active', 'monitoring')")
        
        where_clause = " AND ".join(where_conditions)
        
        # Get episodes for processing - FIXED SQL
        episodes_query = text(f"""
            SELECT ep.id, ep.status, ep.created_at,
                   COUNT(fe.id) as event_count,
                   MAX(fe.start_date) as latest_fire_date,
                   AVG(ST_Y(fe.centroid::geometry)) as lat,
                   AVG(ST_X(fe.centroid::geometry)) as lon,
                   CASE WHEN ep.status = 'active' THEN 1
                        WHEN ep.status = 'monitoring' THEN 2
                        ELSE 3 END as status_priority
            FROM fire_episodes ep
            JOIN fire_episode_events fee ON ep.id = fee.episode_id
            JOIN fire_events fe ON fee.event_id = fe.id
            WHERE {where_clause}
            GROUP BY ep.id, ep.status, ep.created_at
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
