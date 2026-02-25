"""
DT-004: Migrar satellite_images.fire_event_id de ON DELETE CASCADE → SET NULL

Esta migración:
1. Elimina la FK existente con CASCADE.
2. Hace nullable la columna (fire_event_id puede quedar NULL si el evento se elimina).
3. Recrea la FK con ON DELETE SET NULL.

Run:
    python scripts/maintenance/migrate_fk_fire_event_id.py [--dry-run]
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from sqlalchemy import text
from app.db.session import SessionLocal


DDL_STEPS = [
    (
        "Buscar nombre de la FK constraint existente",
        """
        SELECT conname
          FROM pg_constraint
         WHERE conrelid = 'satellite_images'::regclass
           AND contype = 'f'
           AND confrelid = 'fire_events'::regclass
        """,
    ),
]

DROP_FK_TEMPLATE = "ALTER TABLE satellite_images DROP CONSTRAINT {constraint_name};"

ALTER_NULLABLE = """
    ALTER TABLE satellite_images
    ALTER COLUMN fire_event_id DROP NOT NULL;
"""

ADD_FK_SET_NULL = """
    ALTER TABLE satellite_images
    ADD CONSTRAINT satellite_images_fire_event_id_fkey
    FOREIGN KEY (fire_event_id)
    REFERENCES fire_events(id)
    ON DELETE SET NULL;
"""


def main():
    parser = argparse.ArgumentParser(description="DT-004: Migrar FK CASCADE → SET NULL")
    parser.add_argument("--dry-run", action="store_true", help="Solo mostrar DDL, sin ejecutar")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        # 1. Buscar nombre de la constraint existente
        result = db.execute(text("""
            SELECT conname
              FROM pg_constraint
             WHERE conrelid = 'satellite_images'::regclass
               AND contype = 'f'
               AND confrelid = 'fire_events'::regclass
        """)).fetchone()

        if result is None:
            print("No se encontro FK de satellite_images → fire_events. Puede que ya fue migrada.")
            return

        constraint_name = result[0]
        print(f"FK encontrada: {constraint_name}")

        drop_fk = f"ALTER TABLE satellite_images DROP CONSTRAINT {constraint_name};"

        steps = [
            ("DROP FK CASCADE", drop_fk),
            ("ALTER COLUMN fire_event_id DROP NOT NULL", ALTER_NULLABLE.strip()),
            ("ADD FK SET NULL", ADD_FK_SET_NULL.strip()),
        ]

        for step_name, ddl in steps:
            print(f"\n-- {step_name}")
            print(ddl)
            if not args.dry_run:
                db.execute(text(ddl))

        if not args.dry_run:
            db.commit()
            print("\n✓ Migracion aplicada exitosamente.")
        else:
            print("\n[dry-run] No se aplicaron cambios.")

    except Exception as e:
        db.rollback()
        print(f"\n✗ Error: {e}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
