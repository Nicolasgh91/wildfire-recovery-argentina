import argparse
import json
from pathlib import Path

from app.core.alerts import send_alert


def load_coverage(path: Path) -> float | None:
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    totals = data.get("totals", {})
    return totals.get("percent_covered")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", default="coverage.json")
    parser.add_argument("--threshold", type=float, default=60.0)
    args = parser.parse_args()

    path = Path(args.path)
    percent = load_coverage(path)
    if percent is None:
        send_alert("Coverage file missing", f"Missing coverage file: {path}")
        print(f"coverage file not found: {path}")
        return 1

    if percent < args.threshold:
        send_alert(
            "Test coverage below threshold",
            f"Coverage {percent:.2f}% is below {args.threshold:.2f}%",
        )
        print(f"coverage below threshold: {percent:.2f}%")
        return 2

    print(f"coverage OK: {percent:.2f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
