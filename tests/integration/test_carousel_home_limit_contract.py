import json

from sqlalchemy import text


def _upsert_param(db_session, key: str, value: int) -> None:
    db_session.execute(
        text(
            """
            INSERT INTO system_parameters (param_key, param_value, description, category)
            VALUES (:key, CAST(:value AS jsonb), 'test', 'general')
            ON CONFLICT (param_key)
            DO UPDATE SET param_value = EXCLUDED.param_value
            """
        ),
        {"key": key, "value": json.dumps({"value": value})},
    )
    db_session.commit()


def test_home_endpoints_share_canonical_limit_default(client, db_session):
    _upsert_param(db_session, "carousel_home_limit", 7)

    episodes_response = client.get("/api/v1/fire-episodes/active")
    fires_response = client.get("/api/v1/fires/active")

    assert episodes_response.status_code == 200
    assert fires_response.status_code == 200

    episodes_payload = episodes_response.json()
    fires_payload = fires_response.json()

    assert episodes_payload["page_size"] == 7
    assert fires_payload["pagination"]["page_size"] == 7


def test_home_endpoints_allow_explicit_limit_override(client, db_session):
    _upsert_param(db_session, "carousel_home_limit", 7)

    episodes_response = client.get("/api/v1/fire-episodes/active?limit=3")
    fires_response = client.get("/api/v1/fires/active?limit=4")

    assert episodes_response.status_code == 200
    assert fires_response.status_code == 200

    episodes_payload = episodes_response.json()
    fires_payload = fires_response.json()

    assert episodes_payload["page_size"] == 3
    assert fires_payload["pagination"]["page_size"] == 4
