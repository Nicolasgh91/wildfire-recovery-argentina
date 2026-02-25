"""Diagnostic queries for pipeline audit."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

import logging

logging.disable(logging.INFO)

from sqlalchemy import text
from app.db.session import SessionLocal

SEP = "=" * 80
db = SessionLocal()


def p1_insert_h3():
    print(SEP)
    print("P1 - Insertar h3_resolution en system_parameters")
    print(SEP)
    print()

    existing = db.execute(
        text("SELECT param_key, param_value FROM system_parameters WHERE param_key = 'h3_resolution'")
    ).mappings().first()

    if existing:
        print("Ya existe: %s = %s" % (existing["param_key"], existing["param_value"]))
        return

    db.execute(
        text(
            """
            INSERT INTO system_parameters (param_key, param_value, description)
            VALUES (
                'h3_resolution',
                '{"value": 8, "unit": "resolution_level"}'::jsonb,
                'Resolución H3 para indexación espacial de detecciones (0-15, default 8 = ~460m edge)'
            )
            """
        )
    )
    db.commit()
    print("INSERTADO: h3_resolution = {value: 8, unit: resolution_level}")

    verify = db.execute(
        text("SELECT param_key, param_value FROM system_parameters WHERE param_key = 'h3_resolution'")
    ).mappings().first()
    print("Verificacion: %s = %s" % (verify["param_key"], verify["param_value"]))


def p2_causa_raiz():
    print()
    print(SEP)
    print("P2 - Causa raiz: por que no hay episodios active/monitoring")
    print(SEP)
    print()

    # Estado global de episodios
    r = db.execute(
        text(
            """
            SELECT status, COUNT(*) AS cnt
            FROM fire_episodes
            GROUP BY status
            ORDER BY status
            """
        )
    ).mappings().all()
    print("Distribucion de episodios por estado:")
    for row in r:
        print("  %-12s: %s" % (row["status"], row["cnt"]))

    print()

    # Estado global de eventos
    r2 = db.execute(
        text(
            """
            SELECT status, COUNT(*) AS cnt
            FROM fire_events
            GROUP BY status
            ORDER BY status
            """
        )
    ).mappings().all()
    print("Distribucion de eventos por estado:")
    for row in r2:
        print("  %-12s: %s" % (row["status"], row["cnt"]))

    print()

    # Eventos activos: tienen episodio?
    r3 = db.execute(
        text(
            """
            SELECT
                COUNT(*) AS eventos_activos_total,
                COUNT(fee.episode_id) AS con_episodio,
                COUNT(*) - COUNT(fee.episode_id) AS sin_episodio
            FROM fire_events fe
            LEFT JOIN fire_episode_events fee ON fee.event_id = fe.id
            WHERE fe.status = 'active'
            """
        )
    ).mappings().first()
    print("Eventos activos y su vinculacion a episodios:")
    for k, v in dict(r3).items():
        print("  %-30s: %s" % (k, v))

    print()

    # Si hay eventos activos con episodio, que estado tiene el episodio?
    r4 = db.execute(
        text(
            """
            SELECT ep.status AS episode_status, COUNT(DISTINCT ep.id) AS cnt
            FROM fire_events fe
            JOIN fire_episode_events fee ON fee.event_id = fe.id
            JOIN fire_episodes ep ON ep.id = fee.episode_id
            WHERE fe.status = 'active'
            GROUP BY ep.status
            ORDER BY ep.status
            """
        )
    ).mappings().all()
    print("Estado de episodios que CONTIENEN eventos activos:")
    if r4:
        for row in r4:
            print("  %-12s: %s episodios" % (row["episode_status"], row["cnt"]))
    else:
        print("  (ninguno - los eventos activos no tienen episodio)")

    print()

    # Eventos recientes sin episodio (created_at reciente)
    r5 = db.execute(
        text(
            """
            SELECT
                DATE(fe.created_at) AS fecha,
                COUNT(*) AS eventos_creados,
                COUNT(fee.episode_id) AS con_episodio,
                COUNT(*) - COUNT(fee.episode_id) AS sin_episodio
            FROM fire_events fe
            LEFT JOIN fire_episode_events fee ON fee.event_id = fe.id
            WHERE fe.created_at >= NOW() - INTERVAL '7 days'
            GROUP BY DATE(fe.created_at)
            ORDER BY fecha DESC
            """
        )
    ).mappings().all()
    print("Eventos recientes (7d) y vinculacion a episodios:")
    print("  %-12s %10s %12s %12s" % ("fecha", "creados", "con_episodio", "sin_episodio"))
    print("  " + "-" * 50)
    for row in r5:
        print("  %-12s %10s %12s %12s" % (row["fecha"], row["eventos_creados"], row["con_episodio"], row["sin_episodio"]))

    print()

    # Episodios mas recientes con last_seen_at
    r6 = db.execute(
        text(
            """
            SELECT id, status, last_seen_at, start_date, end_date, event_count,
                   EXTRACT(HOURS FROM NOW() - COALESCE(last_seen_at, end_date, start_date))::int AS horas_desde
            FROM fire_episodes
            WHERE status IN ('active', 'monitoring')
            ORDER BY COALESCE(last_seen_at, end_date, start_date) DESC NULLS LAST
            LIMIT 10
            """
        )
    ).mappings().all()
    print("Episodios active/monitoring mas recientes:")
    if r6:
        for row in r6:
            d = dict(row)
            print("  id=%s status=%s last_seen=%s horas=%s events=%s" % (
                str(d["id"])[:8], d["status"], d["last_seen_at"], d["horas_desde"], d["event_count"]))
    else:
        print("  NINGUNO - este es el problema!")

    print()

    # Cuando fue la ultima vez que se ejecuto el pipeline de episodios?
    r7 = db.execute(
        text(
            """
            SELECT MAX(created_at) AS ultimo_episodio_creado,
                   MAX(updated_at) AS ultimo_episodio_actualizado
            FROM fire_episodes
            """
        )
    ).mappings().first()
    print("Timestamps de episodios:")
    print("  Ultimo creado:      %s" % r7["ultimo_episodio_creado"])
    print("  Ultimo actualizado: %s" % r7["ultimo_episodio_actualizado"])

    print()

    # Cuantos eventos fueron creados DESPUES del ultimo episodio creado?
    if r7["ultimo_episodio_creado"]:
        r8 = db.execute(
            text(
                """
                SELECT COUNT(*) AS eventos_post_ultimo_episodio
                FROM fire_events
                WHERE created_at > :ts
                """
            ),
            {"ts": r7["ultimo_episodio_creado"]},
        ).scalar()
        print("Eventos creados DESPUES del ultimo episodio: %s" % r8)

    # Verificar si el recalculo de estados se ejecuta
    r9 = db.execute(
        text(
            """
            SELECT
                COUNT(*) FILTER (WHERE last_seen_at IS NULL) AS sin_last_seen,
                COUNT(*) FILTER (WHERE last_seen_at IS NOT NULL) AS con_last_seen,
                COUNT(*) AS total
            FROM fire_events
            WHERE status = 'active'
            """
        )
    ).mappings().first()
    print()
    print("Eventos activos - cobertura de last_seen_at:")
    for k, v in dict(r9).items():
        print("  %-30s: %s" % (k, v))


def p3_historico():
    print()
    print(SEP)
    print("P3 - Detecciones historicas")
    print(SEP)
    print()

    r = db.execute(
        text(
            """
            SELECT
                EXTRACT(YEAR FROM detected_at)::int AS anio,
                COUNT(*) AS detecciones,
                MIN(detected_at) AS primera,
                MAX(detected_at) AS ultima
            FROM fire_detections
            GROUP BY EXTRACT(YEAR FROM detected_at)
            ORDER BY anio
            """
        )
    ).mappings().all()
    print("Detecciones por anio:")
    print("  %-6s %12s %25s %25s" % ("Anio", "Detecciones", "Primera", "Ultima"))
    print("  " + "-" * 75)
    total = 0
    for row in r:
        d = dict(row)
        print("  %-6s %12s %25s %25s" % (d["anio"], d["detecciones"], d["primera"], d["ultima"]))
        total += d["detecciones"]
    print("  " + "-" * 75)
    print("  %-6s %12s" % ("TOTAL", total))


def p4_det_eventos():
    print()
    print(SEP)
    print("P4 - Agrupacion detecciones -> eventos")
    print(SEP)
    print()

    r = db.execute(
        text(
            """
            SELECT
                EXTRACT(YEAR FROM fe.start_date)::int AS anio,
                COUNT(DISTINCT fe.id) AS eventos,
                SUM(fe.total_detections) AS detecciones_agrupadas,
                AVG(fe.total_detections)::int AS avg_det_por_evento,
                MAX(fe.total_detections) AS max_det_por_evento
            FROM fire_events fe
            GROUP BY EXTRACT(YEAR FROM fe.start_date)
            ORDER BY anio
            """
        )
    ).mappings().all()
    print("Eventos por anio (con detecciones agrupadas):")
    print("  %-6s %10s %12s %10s %10s" % ("Anio", "Eventos", "Detecciones", "Avg/evt", "Max/evt"))
    print("  " + "-" * 55)
    total_e = 0
    total_d = 0
    for row in r:
        d = dict(row)
        det = d["detecciones_agrupadas"] or 0
        print("  %-6s %10s %12s %10s %10s" % (d["anio"], d["eventos"], det, d["avg_det_por_evento"], d["max_det_por_evento"]))
        total_e += d["eventos"]
        total_d += det
    print("  " + "-" * 55)
    print("  %-6s %10s %12s" % ("TOTAL", total_e, total_d))

    print()

    # Detecciones no asignadas
    r2 = db.execute(
        text(
            """
            SELECT
                COUNT(*) AS total_detecciones,
                COUNT(fire_event_id) AS asignadas,
                COUNT(*) - COUNT(fire_event_id) AS sin_evento,
                COUNT(*) FILTER (WHERE is_processed = false) AS no_procesadas
            FROM fire_detections
            """
        )
    ).mappings().first()
    print("Resumen global de asignacion:")
    for k, v in dict(r2).items():
        print("  %-25s: %s" % (k, v))


def p5_eventos_episodios():
    print()
    print(SEP)
    print("P5 - Agrupacion eventos -> episodios")
    print(SEP)
    print()

    r = db.execute(
        text(
            """
            SELECT
                EXTRACT(YEAR FROM ep.start_date)::int AS anio,
                COUNT(DISTINCT ep.id) AS episodios,
                SUM(ep.event_count) AS eventos_agrupados,
                AVG(ep.event_count)::int AS avg_evt_por_episodio,
                MAX(ep.event_count) AS max_evt_por_episodio,
                SUM(ep.detection_count) AS detecciones_totales
            FROM fire_episodes ep
            WHERE ep.status != 'closed'
            GROUP BY EXTRACT(YEAR FROM ep.start_date)
            ORDER BY anio
            """
        )
    ).mappings().all()
    print("Episodios por anio (excl. closed):")
    print("  %-6s %10s %10s %10s %10s %12s" % ("Anio", "Episodios", "Eventos", "Avg/ep", "Max/ep", "Detecciones"))
    print("  " + "-" * 65)
    total_ep = 0
    total_ev = 0
    for row in r:
        d = dict(row)
        ev = d["eventos_agrupados"] or 0
        det = d["detecciones_totales"] or 0
        print("  %-6s %10s %10s %10s %10s %12s" % (
            d["anio"], d["episodios"], ev, d["avg_evt_por_episodio"], d["max_evt_por_episodio"], det))
        total_ep += d["episodios"]
        total_ev += ev
    print("  " + "-" * 65)
    print("  %-6s %10s %10s" % ("TOTAL", total_ep, total_ev))

    print()

    # Eventos sin episodio por anio
    r2 = db.execute(
        text(
            """
            SELECT
                EXTRACT(YEAR FROM fe.start_date)::int AS anio,
                COUNT(*) AS eventos_sin_episodio
            FROM fire_events fe
            LEFT JOIN fire_episode_events fee ON fee.event_id = fe.id
            WHERE fee.event_id IS NULL
            GROUP BY EXTRACT(YEAR FROM fe.start_date)
            ORDER BY anio
            """
        )
    ).mappings().all()
    print("Eventos SIN episodio por anio:")
    print("  %-6s %15s" % ("Anio", "Sin episodio"))
    print("  " + "-" * 25)
    for row in r2:
        print("  %-6s %15s" % (row["anio"], row["eventos_sin_episodio"]))


if __name__ == "__main__":
    p1_insert_h3()
    p2_causa_raiz()
    p3_historico()
    p4_det_eventos()
    p5_eventos_episodios()
    db.close()
