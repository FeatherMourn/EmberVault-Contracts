import json
import re
import tempfile
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
    if (not isinstance(safety, dict) or not isinstance(safety.get("read_only"), bool)
            or not isinstance(safety.get("requires_backup"), bool)
            or not isinstance(safety.get("allowed_profiles"), list)
            or any(not isinstance(item, str) or not item for item in safety.get("allowed_profiles", []))):
        issues.append("safety")
    recovery = value.get("recovery", {})
    if not isinstance(recovery, dict) or any(not isinstance(recovery.get(key), str) or not recovery[key] for key in ("rollback", "verification")):
        issues.append("recovery")
    return issues


class ManifestSchemaTests(unittest.TestCase):
    def test_shared_schemas_use_canonical_namespace(self):
        for name in ("module-manifest.schema.json", "ui-module.schema.json",
                     "worker-result.schema.json", "integration-context.schema.json",
                     "promotion-evidence.schema.json", "evidence-reference.schema.json",
                     "recovery-reference.schema.json", "content-project-export.schema.json"):
            schema = json.loads((ROOT / "schemas" / name).read_text(encoding="utf-8"))
            self.assertTrue(schema["$id"].startswith("https://embervault.dev/contracts/"), name)

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

    def test_content_project_export_contract_is_design_only(self):
        schema = json.loads((ROOT / "schemas" / "content-project-export.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(schema["properties"]["schema_version"]["const"], 1)
        self.assertEqual(schema["properties"]["application_state"]["const"], "design-only")
        self.assertEqual(schema["properties"]["live_game_files_touched"]["const"], False)

    def test_repository_manifest_audit_reports_invalid_module_without_mutation(self):
        from tools.audit_manifests import audit
        with tempfile.TemporaryDirectory() as root:
            module = Path(root) / "EmberVault-Bad"; module.mkdir()
            (module / "module.json").write_text(json.dumps({"id": "bad"}), encoding="utf-8")
            result = audit(root)
            self.assertEqual(len(result), 1)
            self.assertTrue((module / "module.json").exists())

    def test_repository_manifest_audit_accepts_canonical_fixture(self):
        from tools.audit_manifests import audit
        with tempfile.TemporaryDirectory() as root:
            module = Path(root) / "EmberVault-Good"; module.mkdir()
            fixture = (FIXTURES / "module-manifest.valid.json").read_text(encoding="utf-8")
            (module / "module.json").write_text(fixture, encoding="utf-8")
            self.assertEqual(audit(root), {})

    def test_manifest_comparison_is_deterministic_and_read_only(self):
        from tools.compare_manifests import compare
        with tempfile.TemporaryDirectory() as root:
            left = Path(root) / "left" / "EmberVault-Example"
            right = Path(root) / "right" / "EmberVault-Example"
            left.mkdir(parents=True); right.mkdir(parents=True)
            fixture = json.loads((FIXTURES / "module-manifest.valid.json").read_text(encoding="utf-8"))
            (left / "module.json").write_text(json.dumps(fixture), encoding="utf-8")
            fixture["version"] = "2.0.0"
            (right / "module.json").write_text(json.dumps(fixture), encoding="utf-8")
            report = compare(Path(root) / "left", Path(root) / "right")
            self.assertFalse(report["consistent"])
            self.assertEqual(report["metadata_drift"]["embervault.example"]["version"]["left"], "1.0.0")
            self.assertTrue(report["read_only"])


if __name__ == "__main__":
    unittest.main()
