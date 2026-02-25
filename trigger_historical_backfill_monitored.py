#!/usr/bin/env python3
"""
Trigger historical backfill with comprehensive monitoring
"""

import subprocess
import sys
import time
from datetime import datetime

def trigger_historical_backfill():
    """Trigger the historical backfill with monitoring."""
    print("🚀 === TRIGGERING HISTORICAL BACKFILL ===")
    print(f"🚀 Time: {datetime.now()}")
    print("🚀 This will process up to 500 episodes from 2015-2025")
    print("🚀 Expected GEE requests: ~2,500 (5 requests per episode)")
    print("🚀 Expected processing time: ~1 hour for 500 episodes")
    print("🚀 Total episodes to process: ~2,133")
    print()
    
    try:
        # Trigger the backfill task
        result = subprocess.run([
            "docker", "exec", "forestguard-worker-vae",
            "python", "-c",
            "from workers.tasks.recovery import batch_episode_recovery_analysis; "
            "result = batch_episode_recovery_analysis.delay(max_episodes=500, recent_only=False); "
            "print(f'TASK_ID:{result.id}'); "
            "print(f'STATUS:{result.status}');"
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            task_id = None
            status = None
            
            for line in lines:
                if line.startswith('TASK_ID:'):
                    task_id = line.split(':', 1)[1]
                elif line.startswith('STATUS:'):
                    status = line.split(':', 1)[1]
            
            if task_id:
                print(f"✅ Backfill task triggered successfully!")
                print(f"📋 Task ID: {task_id}")
                print(f"📋 Status: {status}")
                print()
                print("🔍 Starting real-time monitoring...")
                print("🔍 Use this command to monitor:")
                print(f"   python monitor_backfill.py {task_id}")
                print()
                print("🔍 Or monitor manually:")
                print("   docker logs -f forestguard-worker-vae")
                print()
                
                # Start monitoring automatically
                print("🔍 Auto-starting monitor (Ctrl+C to stop)...")
                time.sleep(2)
                
                # Import and run monitor
                from monitor_backfill import monitor_backfill
                monitor_backfill(task_id)
                
            else:
                print("❌ Failed to get task ID")
                print(f"Output: {result.stdout}")
                print(f"Error: {result.stderr}")
        else:
            print("❌ Failed to trigger backfill task")
            print(f"Error: {result.stderr}")
            
    except Exception as e:
        print(f"❌ Error triggering backfill: {e}")

if __name__ == "__main__":
    trigger_historical_backfill()
