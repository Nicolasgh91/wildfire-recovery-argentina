from app.schemas.alerts import ClimateSnapshot
from app.services.alerts_service import assess_park_capacity


def test_assess_park_capacity_low_risk():
    assessment = assess_park_capacity(visitor_count=50, carrying_capacity=200, climate=None)

    assert assessment.risk_level == "low"
    assert assessment.alert_level == "normal"
    assert assessment.occupancy_pct == 25.0


def test_assess_park_capacity_high_risk_with_climate():
    climate = ClimateSnapshot(temperature_c=35, wind_speed_kmh=40, humidity_pct=20, drought_index=4)
    assessment = assess_park_capacity(visitor_count=900, carrying_capacity=1000, climate=climate)

    assert assessment.risk_level == "high"
    assert assessment.alert_level == "alert"
    assert assessment.occupancy_pct >= 80.0
