from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.models.fire import FireEvent


def _ensure_public_stats_objects(db_session):
    db_session.execute(text("CREATE SCHEMA IF NOT EXISTS api;"))
    db_session.execute(text("DROP MATERIALIZED VIEW IF EXISTS fire_stats;"))
    db_session.execute(
        text(
            """
            CREATE MATERIALIZED VIEW IF NOT EXISTS fire_stats AS
            SELECT
                date_trunc('day', start_date)::date AS stat_date,
                province,
                COUNT(*)::bigint AS fire_count,
                COALESCE(SUM(estimated_area_hectares), 0) AS total_hectares,
                MAX(max_frp) AS frp_max,
                COALESCE(SUM(sum_frp), 0) AS frp_sum
            FROM fire_events
            WHERE province IS NOT NULL
            GROUP BY 1, 2;
            """
        )
    )
    db_session.execute(
        text(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_fire_stats_stat_date_province
            ON fire_stats(stat_date, province);
            """
        )
    )
    db_session.execute(
        text(
            """
            CREATE OR REPLACE FUNCTION api.get_public_stats(
                p_date_from DATE,
                p_date_to DATE,
                p_province TEXT DEFAULT NULL
            )
            RETURNS TABLE (
                stat_date DATE,
                province TEXT,
                fire_count BIGINT,
                total_hectares NUMERIC,
                frp_max NUMERIC,
                frp_sum NUMERIC
            )
            LANGUAGE plpgsql
            SECURITY DEFINER
            SET search_path = public, api
            AS $$
            BEGIN
                IF p_date_from IS NULL OR p_date_to IS NULL THEN
                    RAISE EXCEPTION 'date_from and date_to are required'
                        USING ERRCODE = 'P0001';
                END IF;

                IF p_date_to - p_date_from > 730 THEN
                    RAISE EXCEPTION 'Date range cannot exceed 730 days'
                        USING ERRCODE = 'P0001';
                END IF;

                IF p_date_to - p_date_from > 90 THEN
                    RETURN QUERY
                    SELECT
                        date_trunc('month', fs.stat_date)::DATE AS stat_date,
                        fs.province::TEXT,
                        SUM(fs.fire_count)::BIGINT,
                        SUM(fs.total_hectares)::NUMERIC,
                        MAX(fs.frp_max)::NUMERIC,
                        SUM(fs.frp_sum)::NUMERIC
                    FROM fire_stats fs
                    WHERE fs.stat_date BETWEEN p_date_from AND p_date_to
                      AND (p_province IS NULL OR fs.province = p_province)
                    GROUP BY date_trunc('month', fs.stat_date), fs.province
                    ORDER BY 1, 2;
                ELSE
                    RETURN QUERY
                    SELECT
                        fs.stat_date::DATE,
                        fs.province::TEXT,
                        fs.fire_count::BIGINT,
                        fs.total_hectares::NUMERIC,
                        fs.frp_max::NUMERIC,
                        fs.frp_sum::NUMERIC
                    FROM fire_stats fs
                    WHERE fs.stat_date BETWEEN p_date_from AND p_date_to
                      AND (p_province IS NULL OR fs.province = p_province)
                    ORDER BY fs.stat_date, fs.province;
                END IF;
            END;
            $$;
            """
        )
    )


def _refresh_fire_stats(db_session):
    db_session.execute(text("REFRESH MATERIALIZED VIEW fire_stats;"))


def test_public_stats_daily_range(db_session):
    _ensure_public_stats_objects(db_session)

    now = datetime.now(timezone.utc)

    fire = FireEvent(
        id=uuid4(),
        start_date=now,
        end_date=now,
        total_detections=3,
        province="Chaco",
        centroid="POINT(-60.0 -27.0)",
        estimated_area_hectares=12.5,
        max_frp=9.1,
        sum_frp=15.2,
    )
    db_session.add(fire)
    db_session.flush()

    _refresh_fire_stats(db_session)

    rows = db_session.execute(
        text("SELECT * FROM api.get_public_stats(:from, :to, :province)"),
        {
            "from": now.date() - timedelta(days=1),
            "to": now.date() + timedelta(days=1),
            "province": None,
        },
    ).fetchall()

    assert any(row.province == "Chaco" for row in rows)
    assert all(row.stat_date == now.date() for row in rows if row.province == "Chaco")


def test_public_stats_monthly_range(db_session):
    _ensure_public_stats_objects(db_session)

    now = datetime.now(timezone.utc)
    jan_date = now.replace(month=1, day=15)
    mar_date = now.replace(month=3, day=10)

    db_session.add_all(
        [
            FireEvent(
                id=uuid4(),
                start_date=jan_date,
                end_date=jan_date,
                total_detections=1,
                province="Chaco",
                centroid="POINT(-60.1 -27.1)",
                estimated_area_hectares=5.0,
                max_frp=3.0,
                sum_frp=3.0,
            ),
            FireEvent(
                id=uuid4(),
                start_date=mar_date,
                end_date=mar_date,
                total_detections=1,
                province="Chaco",
                centroid="POINT(-60.2 -27.2)",
                estimated_area_hectares=7.0,
                max_frp=4.0,
                sum_frp=4.0,
            ),
        ]
    )
    db_session.flush()
    _refresh_fire_stats(db_session)

    rows = db_session.execute(
        text("SELECT * FROM api.get_public_stats(:from, :to, :province)"),
        {
            "from": (jan_date - timedelta(days=10)).date(),
            "to": (jan_date + timedelta(days=120)).date(),
            "province": "Chaco",
        },
    ).fetchall()

    assert rows
    assert all(row.stat_date.day == 1 for row in rows)


def test_public_stats_province_filter(db_session):
    _ensure_public_stats_objects(db_session)

    now = datetime.now(timezone.utc)
    db_session.add_all(
        [
            FireEvent(
                id=uuid4(),
                start_date=now,
                end_date=now,
                total_detections=1,
                province="Chaco",
                centroid="POINT(-60.3 -27.3)",
            ),
            FireEvent(
                id=uuid4(),
                start_date=now,
                end_date=now,
                total_detections=1,
                province="Corrientes",
                centroid="POINT(-58.0 -28.0)",
            ),
        ]
    )
    db_session.flush()
    _refresh_fire_stats(db_session)

    rows = db_session.execute(
        text("SELECT * FROM api.get_public_stats(:from, :to, :province)"),
        {
            "from": now.date() - timedelta(days=1),
            "to": now.date() + timedelta(days=1),
            "province": "Chaco",
        },
    ).fetchall()

    assert rows
    assert all(row.province == "Chaco" for row in rows)


def test_public_stats_range_exceeded(db_session):
    _ensure_public_stats_objects(db_session)

    with pytest.raises(Exception):
        db_session.execute(
            text("SELECT * FROM api.get_public_stats(:from, :to, :province)"),
            {
                "from": date.today() - timedelta(days=800),
                "to": date.today(),
                "province": None,
            },
        ).fetchall()
