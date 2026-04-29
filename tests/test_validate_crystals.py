import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


VALIDATOR_PATH = Path(__file__).resolve().parents[1] / "scripts" / "validate_crystals.py"
SPEC = importlib.util.spec_from_file_location("validate_crystals", VALIDATOR_PATH)
validate_crystals = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(validate_crystals)


def _record(**overrides):
    record = {
        "crystal_id": "xtl-abcdef12",
        "version": "v1",
        "trigger": {"hexagram": "履", "yang_count": 5},
        "outcome": "1x2=home",
        "stats": {"matches": 12, "hits": 10, "rate": 0.833, "ci_95": [0.65, 0.95]},
        "tags": ["football"],
    }
    record.update(overrides)
    return record


def _write_jsonl(path: Path, records):
    path.write_text(
        "".join(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in records),
        encoding="utf-8",
    )


class ValidateCrystalsTest(unittest.TestCase):
    def test_empty_pool_is_valid_prototype_state(self):
        path = self.tmp_path("empty.jsonl")
        path.write_text("", encoding="utf-8")

        self.assertEqual(validate_crystals.validate_jsonl(path), [])

    def test_valid_record_passes(self):
        path = self.tmp_path("valid.jsonl")
        _write_jsonl(path, [_record()])

        self.assertEqual(validate_crystals.validate_jsonl(path), [])

    def test_forbidden_top_level_field_fails(self):
        path = self.tmp_path("forbidden.jsonl")
        record = _record(user_id="user-123")
        _write_jsonl(path, [record])

        errors = validate_crystals.validate_jsonl(path)

        self.assertTrue(any("extra top-level keys" in error for error in errors), errors)
        self.assertTrue(any("forbidden key $.user_id" in error for error in errors), errors)

    def test_forbidden_nested_field_fails(self):
        path = self.tmp_path("nested_forbidden.jsonl")
        record = _record(trigger={"hexagram": "履", "yang_count": 5, "timestamp": "2026-01-01"})
        _write_jsonl(path, [record])

        errors = validate_crystals.validate_jsonl(path)

        self.assertTrue(any("forbidden key $.trigger.timestamp" in error for error in errors), errors)

    def test_duplicate_crystal_id_fails(self):
        path = self.tmp_path("duplicate.jsonl")
        _write_jsonl(path, [_record(), _record()])

        errors = validate_crystals.validate_jsonl(path)

        self.assertTrue(any("duplicate crystal_id xtl-abcdef12" in error for error in errors), errors)

    def test_statistical_thresholds_are_enforced(self):
        path = self.tmp_path("weak_stats.jsonl")
        record = _record(stats={"matches": 2, "hits": 1, "rate": 0.5, "ci_95": [0.3, 0.7]})
        _write_jsonl(path, [record])

        errors = validate_crystals.validate_jsonl(path)

        self.assertTrue(any("stats.matches must be an integer >= 3" in error for error in errors), errors)
        self.assertTrue(any("stats.rate must be a number from 0.60 to 1" in error for error in errors), errors)
        self.assertTrue(any("stats.ci_95 lower bound must be >= 0.55" in error for error in errors), errors)

    def test_rate_must_match_hits_over_matches(self):
        path = self.tmp_path("rate_mismatch.jsonl")
        record = _record(stats={"matches": 10, "hits": 6, "rate": 0.9, "ci_95": [0.56, 0.9]})
        _write_jsonl(path, [record])

        errors = validate_crystals.validate_jsonl(path)

        self.assertTrue(any("stats.rate must match hits/matches" in error for error in errors), errors)

    def tmp_path(self, filename: str) -> Path:
        directory = tempfile.TemporaryDirectory(prefix=f"{self._testMethodName}_")
        self.addCleanup(directory.cleanup)
        return Path(directory.name) / filename


if __name__ == "__main__":
    unittest.main()
