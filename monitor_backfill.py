#!/usr/bin/env python3
"""
Real-time backfill monitoring script for UC-F12 historical backfill
"""

import time
import subprocess
import sys
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def monitor_backfill(task_id):
    """Monitor backfill progress in real-time."""
    logger.info(f"🔍 === MONITORING BACKFILL {task_id} ===")
    
    while True:
        try:
            # Get task status
            result = subprocess.run([
                "docker", "exec", "forestguard-worker-vae",
                "python", "-c",
                f"from workers.celery_app import celery_app; "
                f"task = celery_app.AsyncResult('{task_id}'); "
                f"print(f'STATUS:{task.status}'); "
                f"print(f'RESULT:{task.result}');"
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                status = None
                task_result = None
                
                for line in lines:
                    if line.startswith('STATUS:'):
                        status = line.split(':', 1)[1]
                    elif line.startswith('RESULT:'):
                        task_result = line.split(':', 1)[1]
                
                # Get GEE requests
                gee_requests = get_gee_requests()
                
                # Get database stats
                db_stats = get_database_stats()
                
                # Display progress
                logger.info(f"📊 [{datetime.now().strftime('%H:%M:%S')}] Status: {status}")
                logger.info(f"📊 GEE Requests: {gee_requests}")
                logger.info(f"📊 DB Records: VM={db_stats['vegetation_monitoring']}, LUC={db_stats['land_use_changes']}")
                
                if status == 'SUCCESS':
                    logger.info("🎉 Backfill completed successfully!")
                    break
                elif status == 'FAILURE':
                    logger.error("❌ Backfill failed!")
                    break
                else:
                    logger.info("⏳ Backfill in progress...")
            
            time.sleep(30)  # Check every 30 seconds
            
        except Exception as e:
            logger.error(f"Monitor error: {e}")
            time.sleep(60)

def get_gee_requests():
    """Get current GEE request count."""
    try:
        result = subprocess.run(
            ["docker", "logs", "forestguard-worker-vae", "--tail", "10"],
            capture_output=True, text=True, timeout=10
        )
        
        lines = result.stdout.split('\n')
        for line in reversed(lines):
            if "GEE requests hoy:" in line:
                return int(line.split(':')[-1].strip())
        
        return 0
    except:
        return 0

def get_database_stats():
    """Get current database statistics."""
    try:
        result = subprocess.run([
            "docker", "exec", "forestguard-api", "python", "-c",
            "from app.db.session import SessionLocal; "
            "from sqlalchemy import text; "
            "db = SessionLocal(); "
            "vm = db.execute(text('SELECT count(*) FROM vegetation_monitoring')).scalar(); "
            "luc = db.execute(text('SELECT count(*) FROM land_use_changes')).scalar(); "
            "print(f'VM:{vm},LUC:{luc}'); "
            "db.close();"
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            stats = result.stdout.strip()
            vm, luc = stats.split(',')
            return {
                'vegetation_monitoring': int(vm.split(':')[1]),
                'land_use_changes': int(luc.split(':')[1])
            }
        
        return {'vegetation_monitoring': 0, 'land_use_changes': 0}
    except:
        return {'vegetation_monitoring': 0, 'land_use_changes': 0}

if __name__ == "__main__":
    if len(sys.argv) > 1:
        task_id = sys.argv[1]
        monitor_backfill(task_id)
    else:
        logger.error("Usage: python monitor_backfill.py <task_id>")
