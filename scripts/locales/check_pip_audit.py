import json
import shutil
import subprocess

from app.core.alerts import send_alert


def main() -> int:
    if not shutil.which("pip-audit"):
        print("pip-audit not installed; skipping")
        return 0

    result = subprocess.run(
        ["pip-audit", "-f", "json"],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        send_alert("pip-audit failed", result.stderr.strip() or "pip-audit error")
        print("pip-audit failed")
        return result.returncode

    try:
        data = json.loads(result.stdout or "[]")
    except json.JSONDecodeError:
        send_alert("pip-audit invalid output", "Could not parse JSON output")
        print("pip-audit invalid output")
        return 1

    vuln_count = sum(len(dep.get("vulns", [])) for dep in data)
    if vuln_count:
        send_alert(
            "pip-audit vulnerabilities found",
            f"pip-audit reported {vuln_count} vulnerabilities",
        )
        print(f"pip-audit vulnerabilities: {vuln_count}")
        return 2

    print("pip-audit OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
