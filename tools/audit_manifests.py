"""Audit EmberVault module manifests without importing or executing modules."""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

_schema_tests = Path(__file__).parents[1] / "tests" / "test_schemas.py"
_spec = importlib.util.spec_from_file_location("embervault_contract_manifest_validator", _schema_tests)
if _spec is None or _spec.loader is None:
    raise ImportError("Unable to load canonical manifest validator")
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
validate_manifest = _module.validate_manifest


def audit(root: str | Path) -> dict[str, list[str]]:
    base = Path(root)
    results: dict[str, list[str]] = {}
    for path in sorted(base.glob("EmberVault-*/module.json")):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            issues = validate_manifest(value)
        except (OSError, json.JSONDecodeError) as error:
            issues = [f"unreadable:{error.__class__.__name__}"]
        if issues:
            results[str(path)] = issues
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="Directory containing EmberVault-* module folders")
    args = parser.parse_args()
    failures = audit(args.root)
    if failures:
        for path, issues in failures.items():
            print(f"{path}: {', '.join(issues)}")
        return 1
    print("All EmberVault module manifests passed the canonical contract audit.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
