#!/usr/bin/env python3
"""Generate docs/auth_matrix.md from the AUTH_MATRIX in test_auth_matrix.py (BL-012).

Usage:
    python scripts/generate_auth_matrix.py
"""
from pathlib import Path
import sys

# Add project root to path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.unit.test_auth_matrix import AUTH_MATRIX  # noqa: E402

HEADER = """\
# ForestGuard — Auth Matrix (BL-012)

Endpoint authentication requirements. Auto-generated from `tests/unit/test_auth_matrix.py`.

| Method | Endpoint | Auth |
|--------|----------|------|
"""


def main():
    lines = [HEADER]
    for method, path, auth_type, _kwargs in AUTH_MATRIX:
        lines.append(f"| `{method}` | `{path}` | {auth_type} |\n")

    lines.append(
        "\n> **Validation**: Run `pytest tests/unit/test_auth_matrix.py -v` to verify contract.\n"
        "> **Regenerate**: Run `python scripts/generate_auth_matrix.py` to update this file.\n"
    )

    out_path = ROOT / "docs" / "auth_matrix.md"
    out_path.write_text("".join(lines), encoding="utf-8")
    print(f"Written {out_path}")


if __name__ == "__main__":
    main()
