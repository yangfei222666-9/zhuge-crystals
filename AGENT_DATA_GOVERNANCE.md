# Agent Data Governance

Status: `prototype`

This repository is best understood as a data-governance prototype for Agent experience sharing.

It is not a mature dataset. The current public pool may be empty. The value is the admission rule:

```text
local experience
-> sanitize
-> whitelist schema
-> statistical threshold
-> CI validation
-> human PR review
-> shared public pool
```

## 1. Problem

Agent systems produce useful operational experience, but raw experience is unsafe to share.

Raw logs can include:

- user identity,
- machine fingerprint,
- raw task context,
- provider/API information,
- timestamps and location,
- private notes,
- API keys or secrets,
- high-risk action context.

The goal is to turn local experience into a small, anonymous, structured pattern that can be audited before sharing.

## 2. Public Record Shape

Each public record must be one JSON object per line in `crystals.jsonl`.

Allowed top-level fields:

```json
{
  "crystal_id": "xtl-abc12345",
  "version": "v1",
  "trigger": {
    "hexagram": "履",
    "yang_count": 5
  },
  "outcome": "1x2=home",
  "stats": {
    "matches": 12,
    "hits": 10,
    "rate": 0.833,
    "ci_95": [0.65, 0.95]
  },
  "tags": ["football"]
}
```

No free-text note is allowed in the shared record.

## 3. Forbidden Data

The validator and review policy reject:

- user IDs,
- account names,
- machine IDs,
- match/team names,
- timestamps,
- IP or location,
- provider/API key information,
- raw odds,
- stake or betting amount,
- email,
- free-text comments or notes.

This is intentional. The shared unit is a statistical pattern, not a user log.

## 4. Statistical Admission Gate

Minimum thresholds:

```text
stats.matches >= 3
stats.rate >= 0.60
stats.ci_95[0] >= 0.55
```

The validator also checks:

- strict top-level field whitelist,
- forbidden nested keys,
- `crystal_id` format,
- duplicate `crystal_id`,
- `hits / matches` consistency,
- ordered confidence interval.

## 5. CI Enforcement

GitHub Actions runs:

```bash
python scripts/validate_crystals.py crystals.jsonl
```

This makes the data pool reviewable as code:

```text
invalid schema -> fail CI
forbidden field -> fail CI
weak statistics -> fail CI
duplicate id -> fail CI
```

## 6. Human Review Boundary

CI only validates structure and basic thresholds.

Human review still checks:

- whether the contribution appears anonymized,
- whether the abstract trigger/outcome makes sense,
- whether the pattern is too narrow or noisy,
- whether the contributor accidentally encoded private context.

## 7. Why This Matters For Agent Data Strategy

This repository demonstrates a practical data-governance pattern:

```text
experience contribution
field whitelist
privacy stripping
statistical threshold
automated validation
manual review
shared dataset boundary
```

That maps directly to Agent evaluation and data strategy work:

- how to collect reusable cases,
- how to reject unsafe fields,
- how to keep public data audit-friendly,
- how to separate local raw traces from shared normalized data.

## 8. Boundary

Do not overclaim this repository.

Accurate statement:

```text
I designed a privacy-preserving structured experience-pool prototype with schema whitelist, statistical gates, CI validation, and PR review.
```

Do not say:

```text
Do not claim scaled corpus status.
Do not claim deployed collective intelligence at scale.
Do not claim this data can authorize trading or high-risk decisions.
```
