#!/usr/bin/env python3
"""
UC-F02 validation script (Edge/RPC/RLS) for target environment.

Checks:
1. Edge Function public-stats behavior (status codes and cache headers).
2. Anonymous direct REST access to internal tables is blocked.
3. RPC function exists and is configured as SECURITY DEFINER.
4. RLS and grants are aligned with "no anon direct table access".

Exit codes:
0 -> all checks passed
1 -> one or more checks failed
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from sqlalchemy import create_engine, text

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
REPORT_PATH = ARTIFACTS_DIR / "uc_f02_validation_report.json"


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str
    data: Optional[dict] = None


def load_env_file(env_path: Path) -> Dict[str, str]:
    values: Dict[str, str] = {}
    if not env_path.exists():
        return values

    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            values[key] = value
    return values


def merged_env() -> Dict[str, str]:
    file_values = load_env_file(PROJECT_ROOT / ".env")
    merged = {**file_values, **dict(os.environ)}
    return merged


def build_database_url(env: Dict[str, str]) -> Optional[str]:
    url = env.get("DATABASE_URL")
    if url:
        return url

    host = env.get("DB_HOST")
    user = env.get("DB_USER")
    password = env.get("DB_PASSWORD", "")
    port = env.get("DB_PORT", "5432")
    dbname = env.get("DB_NAME", "postgres")

    if not host or not user:
        return None

    from urllib.parse import quote_plus

    return f"postgresql://{user}:{quote_plus(password)}@{host}:{port}/{dbname}"


def http_request(
    method: str,
    url: str,
    headers: Optional[Dict[str, str]] = None,
    body: Optional[dict] = None,
    timeout: int = 20,
) -> Tuple[int, Dict[str, str], str]:
    request_body = None
    request_headers = headers.copy() if headers else {}

    if body is not None:
        request_body = json.dumps(body).encode("utf-8")
        request_headers.setdefault("Content-Type", "application/json")

    req = Request(url=url, method=method, headers=request_headers, data=request_body)
    try:
        with urlopen(req, timeout=timeout) as resp:
            status = int(resp.status)
            resp_headers = dict(resp.headers.items())
            payload = resp.read().decode("utf-8", errors="replace")
            return status, resp_headers, payload
    except HTTPError as exc:
        payload = exc.read().decode("utf-8", errors="replace")
        return int(exc.code), dict(exc.headers.items()), payload
    except URLError as exc:
        raise RuntimeError(f"Network error for {url}: {exc}") from exc


def check_edge_function(base_url: str) -> List[CheckResult]:
    checks: List[CheckResult] = []

    valid_url = f"{base_url}?{urlencode({'v': '1', 'date_from': '2024-01-01', 'date_to': '2024-01-15'})}"
    status, headers, _ = http_request("GET", valid_url)
    cache_header = headers.get("Cache-Control", "")
    checks.append(
        CheckResult(
            name="edge_valid_range_200",
            passed=status == 200,
            detail=f"status={status}",
        )
    )
    checks.append(
        CheckResult(
            name="edge_cache_headers",
            passed=(
                "s-maxage=3600" in cache_header
                and "stale-while-revalidate=600" in cache_header
                and "stale-if-error=86400" in cache_header
            ),
            detail=f"cache_control={cache_header}",
        )
    )

    invalid_order_url = f"{base_url}?{urlencode({'v': '1', 'date_from': '2024-02-01', 'date_to': '2024-01-01'})}"
    status, _, _ = http_request("GET", invalid_order_url)
    checks.append(
        CheckResult(
            name="edge_invalid_order_400",
            passed=status == 400,
            detail=f"status={status}",
        )
    )

    too_large_url = f"{base_url}?{urlencode({'v': '1', 'date_from': '2020-01-01', 'date_to': '2024-12-31'})}"
    status, _, _ = http_request("GET", too_large_url)
    checks.append(
        CheckResult(
            name="edge_max_730_days",
            passed=status == 400,
            detail=f"status={status}",
        )
    )

    return checks


def check_anon_rest_access(supabase_url: str, anon_key: str) -> List[CheckResult]:
    checks: List[CheckResult] = []
    headers = {"apikey": anon_key, "Authorization": f"Bearer {anon_key}"}

    targets = [
        ("fire_events", "id"),
        ("fire_detections", "id"),
        ("fire_stats", "stat_date"),
    ]
    blocked_status = {401, 403, 404}

    for table, select_col in targets:
        url = f"{supabase_url}/rest/v1/{table}?select={select_col}&limit=1"
        status, _, _ = http_request("GET", url, headers=headers)
        checks.append(
            CheckResult(
                name=f"anon_direct_access_blocked_{table}",
                passed=status in blocked_status,
                detail=f"status={status}",
                data={"status": status},
            )
        )

    return checks


def check_rpc_direct_access(supabase_url: str, anon_key: str) -> List[CheckResult]:
    checks: List[CheckResult] = []
    headers = {"apikey": anon_key, "Authorization": f"Bearer {anon_key}"}

    body = {
        "p_date_from": "2024-01-01",
        "p_date_to": "2024-01-15",
        "p_province": None,
    }
    url = f"{supabase_url}/rest/v1/rpc/get_public_stats"
    status, _, _ = http_request("POST", url, headers=headers, body=body)

    # 200 means exposed through PostgREST; 404 is acceptable if function is only in api schema
    checks.append(
        CheckResult(
            name="rpc_access_mode",
            passed=status in {200, 404},
            detail=f"status={status} (200=public via rest rpc, 404=private schema/not exposed)",
        )
    )
    return checks


def check_db_security(database_url: str) -> List[CheckResult]:
    checks: List[CheckResult] = []
    engine = create_engine(database_url, pool_pre_ping=True)

    try:
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT tablename, rowsecurity
                    FROM pg_tables
                    WHERE schemaname='public'
                      AND tablename IN ('fire_events', 'fire_detections')
                    ORDER BY tablename
                    """
                )
            ).fetchall()

            rls_map = {r[0]: bool(r[1]) for r in rows}
            for table in ("fire_events", "fire_detections"):
                enabled = rls_map.get(table, False)
                checks.append(
                    CheckResult(
                        name=f"rls_enabled_{table}",
                        passed=enabled,
                        detail=f"rowsecurity={enabled}",
                        data={"rowsecurity": enabled},
                    )
                )

            grants = conn.execute(
                text(
                    """
                    SELECT table_name, grantee, privilege_type
                    FROM information_schema.role_table_grants
                    WHERE table_schema='public'
                      AND table_name IN ('fire_events', 'fire_detections')
                      AND grantee IN ('anon', 'authenticated')
                    ORDER BY table_name, grantee, privilege_type
                    """
                )
            ).fetchall()

            has_anon_select = any(
                g[1] == "anon" and g[2] == "SELECT" for g in grants
            )
            checks.append(
                CheckResult(
                    name="anon_select_not_granted_internal_tables",
                    passed=not has_anon_select,
                    detail=f"grant_rows={len(grants)}",
                    data={
                        "grants": [
                            {
                                "table_name": g[0],
                                "grantee": g[1],
                                "privilege_type": g[2],
                            }
                            for g in grants
                        ]
                    },
                )
            )

            fn = conn.execute(
                text(
                    """
                    SELECT n.nspname, p.proname, p.prosecdef,
                           pg_get_function_identity_arguments(p.oid) AS args,
                           p.proacl::text
                    FROM pg_proc p
                    JOIN pg_namespace n ON n.oid = p.pronamespace
                    WHERE n.nspname = 'api' AND p.proname = 'get_public_stats'
                    LIMIT 1
                    """
                )
            ).fetchone()

            fn_exists = fn is not None
            fn_secdef = bool(fn[2]) if fn else False
            fn_acl = fn[4] if fn else ""
            anon_exec = "anon=X/" in fn_acl if fn_acl else False

            checks.append(
                CheckResult(
                    name="rpc_function_exists_api_schema",
                    passed=fn_exists,
                    detail=f"exists={fn_exists}",
                )
            )
            checks.append(
                CheckResult(
                    name="rpc_security_definer",
                    passed=fn_secdef,
                    detail=f"security_definer={fn_secdef}",
                )
            )
            checks.append(
                CheckResult(
                    name="rpc_anon_execute_granted",
                    passed=anon_exec,
                    detail=f"anon_execute={anon_exec}",
                )
            )
    finally:
        engine.dispose()

    return checks


def main() -> int:
    env = merged_env()
    supabase_url = env.get("SUPABASE_URL", "").rstrip("/")
    anon_key = env.get("SUPABASE_ANON_KEY", "")
    public_stats_url = env.get(
        "PUBLIC_STATS_URL", f"{supabase_url}/functions/v1/public-stats"
    )
    database_url = build_database_url(env)

    results: List[CheckResult] = []
    failures: List[str] = []

    if not supabase_url or not anon_key:
        print("ERROR: SUPABASE_URL or SUPABASE_ANON_KEY is not configured.")
        return 1
    if not database_url:
        print("ERROR: DATABASE_URL (or DB_* components) is not configured.")
        return 1

    print(f"UC-F02 validation target: {public_stats_url}")

    for checker in (
        lambda: check_edge_function(public_stats_url),
        lambda: check_anon_rest_access(supabase_url, anon_key),
        lambda: check_rpc_direct_access(supabase_url, anon_key),
        lambda: check_db_security(database_url),
    ):
        try:
            results.extend(checker())
        except Exception as exc:
            failure = f"checker_runtime_error: {type(exc).__name__}: {exc}"
            results.append(
                CheckResult(
                    name="checker_runtime_error",
                    passed=False,
                    detail=failure,
                )
            )

    for item in results:
        status = "PASS" if item.passed else "FAIL"
        print(f"[{status}] {item.name} -> {item.detail}")
        if not item.passed:
            failures.append(item.name)

    ARTIFACTS_DIR.mkdir(exist_ok=True)
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "public_stats_url": public_stats_url,
        "checks": [asdict(r) for r in results],
        "failed_checks": failures,
        "passed": len(failures) == 0,
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Report written: {REPORT_PATH}")

    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
