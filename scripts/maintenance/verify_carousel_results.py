"""
Verifica resultados post-generacion de thumbnails del carousel.
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from sqlalchemy import text
from app.db.session import SessionLocal

db = SessionLocal()
try:
    rows = db.execute(text("""
        SELECT
            id,
            status,
            gee_candidate,
            jsonb_array_length(slides_data) AS slide_count,
            last_seen_at::date AS last_seen,
            extinct_at::date AS extinct_on
        FROM fire_episodes
        WHERE gee_candidate = true
          AND (
            status IN ('active', 'monitoring')
            OR (status = 'extinct' AND extinct_at > NOW() - INTERVAL '30 days')
          )
        ORDER BY slide_count DESC NULLS LAST, status
        LIMIT 25
    """)).mappings().all()

    with_slides = [r for r in rows if r["slide_count"] and r["slide_count"] > 0]
    without_slides = [r for r in rows if not r["slide_count"] or r["slide_count"] == 0]

    print(f"\n=== RESULTADO CAROUSEL ===")
    print(f"Episodios candidatos (active/monitoring/extinct reciente): {len(rows)}")
    print(f"  Con slides_data (visibles en carrusel): {len(with_slides)}")
    print(f"  Sin slides_data (pendientes):           {len(without_slides)}")

    print(f"\n--- Episodios CON slides ---")
    for r in with_slides:
        print(f"  {r['id']} | {r['status']:10} | slides={r['slide_count']} | last_seen={r['last_seen']}")

    if without_slides:
        print(f"\n--- Episodios SIN slides ---")
        for r in without_slides:
            print(f"  {r['id']} | {r['status']:10} | last_seen={r['last_seen']}")

finally:
    db.close()
