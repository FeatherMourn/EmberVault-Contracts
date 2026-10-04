import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas" / "module-manifest.schema.json"
FIXTURES = ROOT / "tests" / "fixtures"
REQUIRED = {
    "id", "name", "version", "publisher", "capabilities", "feature_state",
    "process_mode", "contract_version", "safety", "recovery", "operation_types",
}


def validate_manifest(value: dict) -> list[str]:
    issues = []
    issues.extend(f"missing:{key}" for key in sorted(REQUIRED - value.keys()))
    if not re.fullmatch(r"embervault\.[a-z0-9-]+", str(value.get("id", ""))):
        issues.append("id")
    if value.get("contract_version") != 1:
        issues.append("contract_version")
    if value.get("feature_state") not in {"stable", "verified", "experimental", "research-only", "blocked"}:
        issues.append("feature_state")
    if value.get("process_mode") not in {"embedded", "separate"}:
        issues.append("process_mode")
    for key in ("capabilities", "operation_types"):
        if not isinstance(value.get(key), list) or any(not isinstance(item, str) or not item for item in value.get(key, [])):
            issues.append(key)
    safety = value.get("safety", {})
    if not isinstance(safety, dict) or not isinstance(safety.get("read_only"), bool) or not isinstance(safety.get("requires_backup"), bool):
        issues.append("safety")
    recovery = value.get("recovery", {})
    if not isinstance(recovery, dict) or any(not isinstance(recovery.get(key), str) or not recovery[key] for key in ("rollback", "verification")):
        issues.append("recovery")
    return issues


class ManifestSchemaTests(unittest.TestCase):
    def test_schema_declares_canonical_namespace_and_version(self):
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        self.assertEqual(schema["$id"], "https://embervault.dev/contracts/module-manifest.schema.json")
        self.assertEqual(schema["properties"]["contract_version"]["const"], 1)

    def test_valid_fixture_passes(self):
        value = json.loads((FIXTURES / "module-manifest.valid.json").read_text(encoding="utf-8"))
        self.assertEqual(validate_manifest(value), [])

    def test_invalid_fixture_fails_closed(self):
        value = json.loads((FIXTURES / "module-manifest.invalid.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(validate_manifest(value)), 5)


if __name__ == "__main__":
    unittest.main()
