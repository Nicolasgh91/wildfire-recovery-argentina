#!/usr/bin/env python3
"""
UC-17 Diagnostic Script: Verify fire_episodes status and GEE processing eligibility.

This script helps diagnose why process_satellite_slides.py might not find episodes.
Run this AFTER aggregate_fire_episodes.py to verify the data state.

Usage:
    python diagnose_episodes.py
    python diagnose_episodes.py --fix-status  # Recalculate status based on events
"""

import argparse
import logging
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=BASE_DIR / ".env")

LOG = logging.getLogger(__name__)
EPISODE_MONITORING_DAYS = 15


def build_db_url() -> str | URL:
    if os.getenv("DB_HOST") and os.getenv("DB_PASSWORD"):
        return URL.create(
            "postgresql",
            username=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST"),
            port=int(os.getenv("DB_PORT", 5432)),
            database=os.getenv("DB_NAME", "postgres"),
        )
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url.replace("postgres://", "postgresql://", 1)
    raise ValueError("Database credentials not found")


def get_engine():
    return create_engine(build_db_url(), pool_pre_ping=True)


def normalize_datetime(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def check_tables_exist(engine) -> dict:
    """Verify if fire_episodes tables exist."""
    result = {"fire_episodes": False, "fire_episode_events": False}
    
    sql = text("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name IN ('fire_episodes', 'fire_episode_events')
    """)
    
    with engine.connect() as conn:
        rows = conn.execute(sql).fetchall()
        for row in rows:
            result[row[0]] = True
    
    return result


def get_episode_stats(engine) -> dict:
    """Get statistics about episodes."""
    stats = {}
    
    # Total episodes
    with engine.connect() as conn:
        row = conn.execute(text("SELECT COUNT(*) FROM fire_episodes")).fetchone()
        stats["total_episodes"] = row[0]
        
        # By status
        rows = conn.execute(text("""
            SELECT status, COUNT(*) 
            FROM fire_episodes 
            GROUP BY status
        """)).fetchall()
        stats["by_status"] = {r[0]: r[1] for r in rows}
        
        # GEE candidates
        row = conn.execute(text("""
            SELECT COUNT(*) FROM fire_episodes WHERE gee_candidate = true
        """)).fetchone()
        stats["gee_candidates"] = row[0]
        
        # GEE candidates by status
        rows = conn.execute(text("""
            SELECT status, COUNT(*) 
            FROM fire_episodes 
            WHERE gee_candidate = true
            GROUP BY status
        """)).fetchall()
        stats["gee_candidates_by_status"] = {r[0]: r[1] for r in rows}
        
        # Date ranges
        row = conn.execute(text("""
            SELECT 
                MIN(start_date) as min_start,
                MAX(end_date) as max_end,
                NOW() as current_time
            FROM fire_episodes
        """)).fetchone()
        stats["date_range"] = {
            "earliest_start": row[0],
            "latest_end": row[1],
            "current_time": row[2]
        }
        
        # Episodes with end_date >= NOW()
        row = conn.execute(text("""
            SELECT COUNT(*) FROM fire_episodes WHERE end_date >= NOW()
        """)).fetchone()
        stats["episodes_with_future_end_date"] = row[0]
        
    return stats


def get_sample_episodes(engine, limit: int = 5) -> list:
    """Get sample episodes for inspection."""
    sql = text("""
        SELECT 
            id,
            status,
            start_date,
            end_date,
            event_count,
            gee_candidate,
            gee_priority,
            provinces
        FROM fire_episodes
        ORDER BY gee_priority NULLS LAST, end_date DESC
        LIMIT :limit
    """)
    
    with engine.connect() as conn:
        rows = conn.execute(sql, {"limit": limit}).mappings().all()
        return [dict(r) for r in rows]


def fix_episode_status(engine, dry_run: bool = True) -> int:
    """
    Recalculate episode status based on constituent fire_events.

    Rules:
    - active: at least one event is active
    - monitoring: no active events and last extinguished < EPISODE_MONITORING_DAYS
    - extinct: no active events and last extinguished >= EPISODE_MONITORING_DAYS
    - closed: no remaining events linked to the episode
    """
    sql_select = text("""
        SELECT
            fe.id as episode_id,
            fe.status as current_status,
            COUNT(ev.id) as event_count,
            MAX(CASE WHEN ev.status = 'active' THEN 1 ELSE 0 END) as has_active_events,
            MAX(COALESCE(ev.extinguished_at, ev.end_date)) as last_extinguished
        FROM fire_episodes fe
        LEFT JOIN fire_episode_events fee ON fee.episode_id = fe.id
        LEFT JOIN fire_events ev ON ev.id = fee.event_id
        GROUP BY fe.id, fe.status
    """)
    
    sql_update = text("""
        UPDATE fire_episodes fe
        SET
            status = CASE
                WHEN NOT EXISTS (
                    SELECT 1 FROM fire_episode_events fee
                    WHERE fee.episode_id = fe.id
                ) THEN 'closed'
                WHEN EXISTS (
                    SELECT 1 FROM fire_episode_events fee
                    JOIN fire_events ev ON ev.id = fee.event_id
                    WHERE fee.episode_id = fe.id AND ev.status = 'active'
                ) THEN 'active'
                WHEN (
                    SELECT MAX(COALESCE(ev.extinguished_at, ev.end_date))
                    FROM fire_episode_events fee
                    JOIN fire_events ev ON ev.id = fee.event_id
                    WHERE fee.episode_id = fe.id
                ) >= NOW() - (:monitoring_days * INTERVAL '1 day') THEN 'monitoring'
                ELSE 'extinct'
            END,
            end_date = (
                SELECT MAX(ev.end_date)
                FROM fire_episode_events fee
                JOIN fire_events ev ON ev.id = fee.event_id
                WHERE fee.episode_id = fe.id
            ),
            updated_at = NOW()
        WHERE id = :episode_id
        RETURNING id, status
    """)
    
    updated_count = 0
    to_update = 0
    
    with engine.connect() as conn:
        episodes = conn.execute(sql_select).mappings().all()
        
        now = datetime.now(timezone.utc)
        monitoring_window = timedelta(days=EPISODE_MONITORING_DAYS)

        for ep in episodes:
            if ep["event_count"] == 0:
                expected_status = "closed"
            elif ep["has_active_events"]:
                expected_status = "active"
            else:
                last_extinguished = normalize_datetime(ep["last_extinguished"])
                if last_extinguished and now - last_extinguished < monitoring_window:
                    expected_status = "monitoring"
                else:
                    expected_status = "extinct"

            if ep["current_status"] != expected_status:
                LOG.info(f"Episode {ep['episode_id'][:8]}...: {ep['current_status']} -> {expected_status}")
                to_update += 1
                if not dry_run:
                    conn.execute(
                        sql_update,
                        {"episode_id": ep["episode_id"], "monitoring_days": EPISODE_MONITORING_DAYS},
                    )
                    updated_count += 1
        
        if not dry_run:
            conn.commit()
    
    return updated_count if not dry_run else to_update


def print_diagnostic_report(engine):
    """Print comprehensive diagnostic report."""
    print("\n" + "=" * 70)
    print("🔍 UC-17 EPISODE DIAGNOSTIC REPORT")
    print("=" * 70)
    
    # Check tables
    print("\n📋 TABLE STATUS:")
    tables = check_tables_exist(engine)
    for table, exists in tables.items():
        status = "✅ EXISTS" if exists else "❌ MISSING"
        print(f"   {table}: {status}")
    
    if not all(tables.values()):
        print("\n⚠️  CRITICAL: Missing tables! Run fire_episodes_migration.sql first.")
        return
    
    # Get stats
    stats = get_episode_stats(engine)
    
    print(f"\n📊 EPISODE STATISTICS:")
    print(f"   Total Episodes: {stats['total_episodes']}")
    print(f"   By Status: {stats['by_status']}")
    print(f"   GEE Candidates: {stats['gee_candidates']}")
    print(f"   GEE Candidates by Status: {stats['gee_candidates_by_status']}")
    
    print(f"\n📅 DATE ANALYSIS:")
    dr = stats['date_range']
    print(f"   Earliest Start: {dr['earliest_start']}")
    print(f"   Latest End: {dr['latest_end']}")
    print(f"   Current Time: {dr['current_time']}")
    print(f"   Episodes with end_date >= NOW(): {stats['episodes_with_future_end_date']}")
    
    # Root cause detection
    print(f"\n🎯 ROOT CAUSE ANALYSIS:")
    
    active_count = stats['by_status'].get('active', 0)
    monitoring_count = stats['by_status'].get('monitoring', 0)
    extinct_count = stats['by_status'].get('extinct', 0)
    closed_count = stats['by_status'].get('closed', 0)
    gee_active = stats['gee_candidates_by_status'].get('active', 0)
    gee_monitoring = stats['gee_candidates_by_status'].get('monitoring', 0)
    gee_extinct = stats['gee_candidates_by_status'].get('extinct', 0)

    if stats['total_episodes'] == 0:
        print("   ? No episodes exist! Run aggregate_fire_episodes.py first.")
    elif active_count == 0 and monitoring_count == 0 and extinct_count == 0:
        print("   ? ALL episodes have status='closed' (no linked events)")
        print("   ??  process_satellite_slides.py --mode active will find NOTHING")
        print("   ??  process_satellite_slides.py --mode historic needs --days-back=N")
    elif active_count == 0:
        print("   ??  No active episodes found.")
        print("   ??  process_satellite_slides.py --mode active will find NOTHING")
        if monitoring_count or extinct_count:
            print(f"   ? Found {monitoring_count} monitoring and {extinct_count} extinct episodes")
            print("   ??  process_satellite_slides.py --mode historic --days-back=30")
            if (gee_monitoring + gee_extinct) > 0:
                print(f"   ?? TIP: {gee_monitoring + gee_extinct} GEE candidates are historic")
    else:
        print(f"   ? Found {active_count} active episodes ({gee_active} are GEE candidates)")

    # Sample episodes
    print(f"\n📝 SAMPLE EPISODES (Top 5 by priority):")
    samples = get_sample_episodes(engine, 5)
    for ep in samples:
        gee_flag = "🎯" if ep['gee_candidate'] else "  "
        print(f"   {gee_flag} {str(ep['id'])[:8]}... | {ep['status']:8} | "
              f"events={ep['event_count']:3} | prio={ep['gee_priority'] or 'N/A'}")
    
    print("\n" + "=" * 70)


def main():
    parser = argparse.ArgumentParser(description="UC-17 Episode Diagnostic Tool")
    parser.add_argument("--fix-status", action="store_true", 
                       help="Recalculate episode status based on fire_events")
    parser.add_argument("--dry-run", action="store_true", default=True,
                       help="Don't actually update (default: True)")
    parser.add_argument("--apply", action="store_true",
                       help="Actually apply status fixes")
    
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    
    engine = get_engine()
    
    print_diagnostic_report(engine)
    
    if args.fix_status:
        dry_run = not args.apply
        print(f"\n{'[DRY RUN] ' if dry_run else ''}Fixing episode statuses...")
        count = fix_episode_status(engine, dry_run=dry_run)
        if dry_run:
            print(f"   Would update {count} episodes. Use --apply to commit changes.")
        else:
            print(f"   Updated {count} episodes.")


if __name__ == "__main__":
    main()
