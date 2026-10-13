"""Compare standalone EmberVault manifests with the Control Center bundle."""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any

_comparison_path = Path(__file__).with_name("compare_manifests.py")
_spec = importlib.util.spec_from_file_location("embervault_manifest_comparison", _comparison_path)
if _spec is None or _spec.loader is None:
    raise ImportError("Unable to load manifest comparison helper")
_comparison = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_comparison)
CRITICAL_FIELDS = _comparison.CRITICAL_FIELDS


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _index(paths: list[Path]) -> dict[str, dict[str, Any]]:
    result = {}
    for path in paths:
        value = _read(path)
        if isinstance(value.get("id"), str):
            result[value["id"]] = value
    return result


def audit_suite(root: str | Path) -> dict[str, Any]:
    base = Path(root)
    standalone = _index([
        path for path in sorted(base.glob("EmberVault-*/module.json"))
        if path.name != "EmberVault-Control-Center"
    ])
    bundled = _index(sorted((base / "EmberVault-Control-Center" / "modules").glob("*/module.json")))
    missing_standalone = sorted(set(bundled) - set(standalone))
    missing_bundled = sorted(set(standalone) - set(bundled))
    critical_drift: dict[str, dict[str, Any]] = {}
    for module_id in sorted(set(standalone) & set(bundled)):
        fields = {}
        for field in sorted(CRITICAL_FIELDS):
            if standalone[module_id].get(field) != bundled[module_id].get(field):
                fields[field] = {"standalone": standalone[module_id].get(field), "bundled": bundled[module_id].get(field)}
        if fields:
            critical_drift[module_id] = fields
    return {
        "comparison_version": 1,
        "standalone_count": len(standalone),
        "bundled_count": len(bundled),
        "missing_standalone": missing_standalone,
        "missing_bundled": missing_bundled,
        "bundled_only": missing_standalone,
        "critical_drift": critical_drift,
        "consistent": not missing_bundled and not critical_drift,
        "read_only": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    report = audit_suite(args.root)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["consistent"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
