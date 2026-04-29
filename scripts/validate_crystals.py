#!/usr/bin/env python3
"""Validate the public crystal JSONL pool.

This repository is a public data pool. The validator intentionally uses only the
Python standard library so GitHub Actions can run it without dependency drift.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


ALLOWED_TOP_LEVEL_KEYS = {
    "crystal_id",
    "version",
    "trigger",
    "outcome",
    "stats",
    "tags",
}

FORBIDDEN_KEYS = {
    "api_key",
    "comment",
    "created_at",
    "discovered_by",
    "email",
    "ip",
    "location",
    "machine_id",
    "match_name",
    "note",
    "odds",
    "provider",
    "stake",
    "team",
    "timestamp",
    "user",
    "user_id",
}

CRYSTAL_ID_RE = re.compile(r"^xtl-[0-9a-f]{8}$")


def _fail(errors: list[str], line_no: int, message: str) -> None:
    errors.append(f"line {line_no}: {message}")


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _scan_forbidden_keys(value: Any, *, line_no: int, errors: list[str], path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).lower()
            if normalized in FORBIDDEN_KEYS:
                _fail(errors, line_no, f"forbidden key {path}.{key}")
            _scan_forbidden_keys(child, line_no=line_no, errors=errors, path=f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _scan_forbidden_keys(child, line_no=line_no, errors=errors, path=f"{path}[{index}]")


def validate_record(record: Any, *, line_no: int, seen_ids: set[str], errors: list[str]) -> None:
    if not isinstance(record, dict):
        _fail(errors, line_no, "record must be a JSON object")
        return

    keys = set(record)
    missing = sorted(ALLOWED_TOP_LEVEL_KEYS - keys)
    extra = sorted(keys - ALLOWED_TOP_LEVEL_KEYS)
    if missing:
        _fail(errors, line_no, f"missing required keys: {', '.join(missing)}")
    if extra:
        _fail(errors, line_no, f"extra top-level keys are not allowed: {', '.join(extra)}")

    _scan_forbidden_keys(record, line_no=line_no, errors=errors)

    crystal_id = record.get("crystal_id")
    if not isinstance(crystal_id, str) or not CRYSTAL_ID_RE.fullmatch(crystal_id):
        _fail(errors, line_no, "crystal_id must match xtl-[0-9a-f]{8}")
    elif crystal_id in seen_ids:
        _fail(errors, line_no, f"duplicate crystal_id {crystal_id}")
    else:
        seen_ids.add(crystal_id)

    if record.get("version") != "v1":
        _fail(errors, line_no, "version must be v1")

    trigger = record.get("trigger")
    if not isinstance(trigger, dict):
        _fail(errors, line_no, "trigger must be an object")
    else:
        if set(trigger) != {"hexagram", "yang_count"}:
            _fail(errors, line_no, "trigger must contain only hexagram and yang_count")
        if not isinstance(trigger.get("hexagram"), str) or not trigger.get("hexagram"):
            _fail(errors, line_no, "trigger.hexagram must be a non-empty string")
        yang_count = trigger.get("yang_count")
        if not isinstance(yang_count, int) or isinstance(yang_count, bool) or not 0 <= yang_count <= 6:
            _fail(errors, line_no, "trigger.yang_count must be an integer from 0 to 6")

    outcome = record.get("outcome")
    if not isinstance(outcome, str) or not outcome:
        _fail(errors, line_no, "outcome must be a non-empty string")

    stats = record.get("stats")
    if not isinstance(stats, dict):
        _fail(errors, line_no, "stats must be an object")
    else:
        if set(stats) != {"matches", "hits", "rate", "ci_95"}:
            _fail(errors, line_no, "stats must contain only matches, hits, rate and ci_95")
        matches = stats.get("matches")
        hits = stats.get("hits")
        rate = stats.get("rate")
        ci_95 = stats.get("ci_95")
        if not isinstance(matches, int) or isinstance(matches, bool) or matches < 3:
            _fail(errors, line_no, "stats.matches must be an integer >= 3")
        if not isinstance(hits, int) or isinstance(hits, bool) or not isinstance(matches, int) or hits < 0 or hits > matches:
            _fail(errors, line_no, "stats.hits must be an integer between 0 and matches")
        if not _is_number(rate) or rate < 0.60 or rate > 1:
            _fail(errors, line_no, "stats.rate must be a number from 0.60 to 1")
        if isinstance(matches, int) and isinstance(hits, int) and _is_number(rate):
            calculated_rate = round(hits / matches, 3)
            if abs(rate - calculated_rate) > 0.002:
                _fail(errors, line_no, f"stats.rate must match hits/matches rounded to 3 decimals ({calculated_rate})")
        if not isinstance(ci_95, list) or len(ci_95) != 2 or not all(_is_number(item) for item in ci_95):
            _fail(errors, line_no, "stats.ci_95 must be a two-number array")
        elif not (0 <= ci_95[0] <= ci_95[1] <= 1):
            _fail(errors, line_no, "stats.ci_95 must be ordered within [0, 1]")
        elif ci_95[0] < 0.55:
            _fail(errors, line_no, "stats.ci_95 lower bound must be >= 0.55")

    tags = record.get("tags")
    if not isinstance(tags, list) or not tags or not all(isinstance(tag, str) and tag for tag in tags):
        _fail(errors, line_no, "tags must be a non-empty string array")


def validate_jsonl(path: Path) -> list[str]:
    errors: list[str] = []
    seen_ids: set[str] = set()
    if not path.exists():
        return [f"{path}: file does not exist"]

    with path.open("r", encoding="utf-8") as handle:
        for line_no, raw_line in enumerate(handle, 1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                _fail(errors, line_no, f"invalid JSON: {exc.msg}")
                continue
            validate_record(record, line_no=line_no, seen_ids=seen_ids, errors=errors)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate zhuge-crystals public JSONL data.")
    parser.add_argument("path", nargs="?", default="crystals.jsonl", help="JSONL file to validate")
    args = parser.parse_args()

    errors = validate_jsonl(Path(args.path))
    if errors:
        print("crystal validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"crystal validation ok: {args.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
