"""Compare two EmberVault module-manifest roots without executing modules."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


IGNORED_FIELDS = {"entrypoint", "executable", "application_entrypoint", "launcher", "minimum_core_version"}
CRITICAL_FIELDS = {"version", "feature_state", "contract_version", "safety"}


def load_manifests(root: str | Path) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for path in sorted(Path(root).rglob("module.json")):
        value = json.loads(path.read_text(encoding="utf-8"))
        module_id = value.get("id")
        if isinstance(module_id, str) and module_id:
            result[module_id] = value
    return result


def compare(left: str | Path, right: str | Path) -> dict[str, Any]:
    left_values = load_manifests(left)
    right_values = load_manifests(right)
    module_ids = sorted(set(left_values) | set(right_values))
    missing_left = sorted(set(right_values) - set(left_values))
    missing_right = sorted(set(left_values) - set(right_values))
    drift: dict[str, dict[str, Any]] = {}
    critical_drift: dict[str, dict[str, Any]] = {}
    for module_id in sorted(set(left_values) & set(right_values)):
        fields = {}
        for field in sorted(set(left_values[module_id]) | set(right_values[module_id])):
            if field in IGNORED_FIELDS:
                continue
            if left_values[module_id].get(field) != right_values[module_id].get(field):
                fields[field] = {"left": left_values[module_id].get(field), "right": right_values[module_id].get(field)}
        if fields:
            drift[module_id] = fields
            critical = {field: value for field, value in fields.items() if field in CRITICAL_FIELDS}
            if critical:
                critical_drift[module_id] = critical
    return {
        "comparison_version": 1,
        "module_count": len(module_ids),
        "missing_left": missing_left,
        "missing_right": missing_right,
        "metadata_drift": drift,
        "consistent": not missing_left and not missing_right and not critical_drift,
        "metadata_consistent": not missing_left and not missing_right and not drift,
        "critical_drift": critical_drift,
        "read_only": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("left", type=Path)
    parser.add_argument("right", type=Path)
    args = parser.parse_args()
    report = compare(args.left, args.right)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["consistent"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
