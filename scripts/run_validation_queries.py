"""Run all validation queries from the audit correction plan."""

from dotenv import load_dotenv

load_dotenv()

import logging

logging.disable(logging.INFO)

from sqlalchemy import text
from app.db.session import SessionLocal

SEP = "=" * 80


def run_all():
    db = SessionLocal()

    # ------------------------------------------------------------------
    # Q4 — Relacion episodios-eventos
    # ------------------------------------------------------------------
    print(SEP)
    print("Q4 - Verificar relacion episodios-eventos")
    print(SEP)
    print()

    r = db.execute(
        text(
            """
            SELECT e.id, e.status, e.event_count, e.created_at
            FROM fire_episodes e
            LEFT JOIN fire_episode_events fee ON fee.episode_id = e.id
            WHERE fee.episode_id IS NULL
              AND e.status NOT IN ('closed')
            ORDER BY e.created_at DESC
            LIMIT 10
            """
        )
    ).mappings().all()

    print("Episodios huerfanos (sin eventos, no closed):")
    if r:
        for row in r:
            d = dict(row)
            print(
                "  id=%s status=%s event_count=%s created=%s"
                % (str(d["id"])[:8], d["status"], d["event_count"], d["created_at"])
            )
        print("  Total: %d" % len(r))
    else:
        print("  Ninguno (OK)")
    print()

    r2 = db.execute(
        text(
            """
            SELECT COUNT(*) AS total
            FROM fire_events fe
            LEFT JOIN fire_episode_events fee ON fee.event_id = fe.id
            WHERE fee.event_id IS NULL
              AND fe.created_at >= NOW() - INTERVAL '30 days'
            """
        )
    ).scalar()
    print("Eventos sin episodio (30 dias): %s" % r2)

    # ------------------------------------------------------------------
    # Q5 — Fusiones de episodios
    # ------------------------------------------------------------------
    print()
    print(SEP)
    print("Q5 - Verificar fusiones de episodios")
    print(SEP)
    print()

    exists = db.execute(
        text(
            """
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = 'episode_mergers'
            )
            """
        )
    ).scalar()

    if not exists:
        print("Tabla episode_mergers: NO EXISTE")
    else:
        total = db.execute(text("SELECT COUNT(*) FROM episode_mergers")).scalar()
        print("Total fusiones registradas: %s" % total)

        if total and total > 0:
            r3 = db.execute(
                text(
                    """
                    SELECT
                        em.merged_at,
                        em.reason,
                        ea.status AS absorbed_status,
                        eb.status AS absorbing_status
                    FROM episode_mergers em
                    JOIN fire_episodes ea ON ea.id = em.absorbed_episode_id
                    JOIN fire_episodes eb ON eb.id = em.absorbing_episode_id
                    ORDER BY em.merged_at DESC
                    LIMIT 5
                    """
                )
            ).mappings().all()
            print()
            print("Ultimas fusiones:")
            for row in r3:
                d = dict(row)
                print(
                    "  %s | reason=%s | absorbed=%s | absorbing=%s"
                    % (d["merged_at"], d["reason"], d["absorbed_status"], d["absorbing_status"])
                )

            bad = db.execute(
                text(
                    """
                    SELECT COUNT(*) FROM episode_mergers em
                    JOIN fire_episodes e ON e.id = em.absorbed_episode_id
                    WHERE e.status != 'closed'
                    """
                )
            ).scalar()
            print()
            status = "(OK)" if bad == 0 else "(INCONSISTENCIA!)"
            print("Episodios absorbidos NO en closed: %s %s" % (bad, status))

    # ------------------------------------------------------------------
    # Q6 — Coherencia de estados
    # ------------------------------------------------------------------
    print()
    print(SEP)
    print("Q6 - Verificar coherencia de estados")
    print(SEP)
    print()

    r6a = db.execute(
        text(
            """
            SELECT id, status, last_seen_at, end_date,
                   EXTRACT(HOURS FROM NOW() - COALESCE(last_seen_at, end_date, start_date))::int AS horas_desde_actividad
            FROM fire_events
            WHERE status = 'active'
              AND COALESCE(last_seen_at, end_date, start_date) < NOW() - INTERVAL '168 hours'
            ORDER BY COALESCE(last_seen_at, end_date, start_date) ASC
            LIMIT 10
            """
        )
    ).mappings().all()

    print("Eventos 'active' con actividad > 168h (deberian ser monitoring/extinct):")
    if r6a:
        for row in r6a:
            d = dict(row)
            print(
                "  id=%s horas=%s last_seen=%s"
                % (str(d["id"])[:8], d["horas_desde_actividad"], d["last_seen_at"])
            )
        print("  Total: %d (REQUIERE RECALCULO)" % len(r6a))
    else:
        print("  Ninguno (OK)")
    print()

    r6a_count = db.execute(
        text(
            """
            SELECT COUNT(*) FROM fire_events
            WHERE status = 'active'
              AND COALESCE(last_seen_at, end_date, start_date) < NOW() - INTERVAL '168 hours'
            """
        )
    ).scalar()
    print("Total eventos activos vencidos: %s" % r6a_count)
    print()

    r6b = db.execute(
        text(
            """
            SELECT e.id, e.status AS episode_status,
                   ARRAY_AGG(DISTINCT fe.status) AS event_statuses
            FROM fire_episodes e
            JOIN fire_episode_events fee ON fee.episode_id = e.id
            JOIN fire_events fe ON fe.id = fee.event_id
            WHERE e.status = 'active'
            GROUP BY e.id, e.status
            HAVING NOT ('active' = ANY(ARRAY_AGG(fe.status)))
            LIMIT 10
            """
        )
    ).mappings().all()
    print("Episodios 'active' sin eventos activos:")
    if r6b:
        for row in r6b:
            d = dict(row)
            print(
                "  id=%s event_statuses=%s"
                % (str(d["id"])[:8], d["event_statuses"])
            )
        print("  Total: %d (INCONSISTENCIA)" % len(r6b))
    else:
        print("  Ninguno (OK)")

    # ------------------------------------------------------------------
    # Q7 — Carrusel (slides_data)
    # ------------------------------------------------------------------
    print()
    print(SEP)
    print("Q7 - Verificar carrusel (slides_data)")
    print(SEP)
    print()

    r7a = db.execute(
        text(
            """
            SELECT
                status,
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE slides_data IS NOT NULL AND jsonb_array_length(slides_data) > 0) AS con_slides,
                COUNT(*) FILTER (WHERE gee_candidate = true) AS gee_candidates
            FROM fire_episodes
            GROUP BY status
            ORDER BY status
            """
        )
    ).mappings().all()
    print("Distribucion de slides por estado:")
    print("  %-12s %8s %10s %14s" % ("status", "total", "con_slides", "gee_candidate"))
    print("  " + "-" * 50)
    for row in r7a:
        d = dict(row)
        print(
            "  %-12s %8s %10s %14s"
            % (d["status"], d["total"], d["con_slides"], d["gee_candidates"])
        )

    print()
    r7b = db.execute(
        text(
            """
            SELECT COUNT(*) AS pendientes
            FROM fire_episodes
            WHERE status IN ('active', 'monitoring')
              AND gee_candidate = true
              AND (slides_data IS NULL OR jsonb_array_length(slides_data) = 0)
            """
        )
    ).scalar()
    print("Episodios gee_candidate sin slides (pendientes carrusel): %s" % r7b)

    # ------------------------------------------------------------------
    # Q8 — system_parameters
    # ------------------------------------------------------------------
    print()
    print(SEP)
    print("Q8 - Verificar system_parameters")
    print(SEP)
    print()

    r8 = db.execute(
        text(
            """
            SELECT param_key, param_value
            FROM system_parameters
            WHERE param_key IN (
                'event_spatial_epsilon_meters',
                'event_temporal_window_hours',
                'event_monitoring_window_hours',
                'episode_spatial_epsilon_meters',
                'episode_temporal_window_hours',
                'h3_resolution',
                'carousel_home_limit',
                'carousel_batch_size'
            )
            ORDER BY param_key
            """
        )
    ).mappings().all()

    print("Parametros canonicos del pipeline:")
    for row in r8:
        d = dict(row)
        print("  %-40s: %s" % (d["param_key"], d["param_value"]))

    if not r8:
        print("  (ninguno encontrado - tabla vacia o parametros no insertados)")

    db.close()
    print()
    print(SEP)
    print("VALIDACION COMPLETA")
    print(SEP)


if __name__ == "__main__":
    run_all()
