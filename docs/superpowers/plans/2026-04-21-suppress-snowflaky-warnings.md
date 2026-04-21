# Suppress Snowflaky SyntaxWarnings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `warnings.warn(SyntaxWarning)` for unsupported multi-part identifiers in `snowflaky()` with `logger.debug()` so the flood of Airbyte staging-table warnings is silenced in normal operation without changing any functional behaviour.

**Architecture:** A single-line change in `snowflake_connector.py` replaces the `warnings.warn` call (for the >3 name-parts branch) with `logger.debug`. The existing `GLOBAL_LOGGER` is already imported in that file. One test block that asserts `pytest.warns(SyntaxWarning)` must be updated to assert no warning is raised but the function still returns a value.

**Tech Stack:** Python 3.8+, `warnings` stdlib, `logging` stdlib, `pytest`, `pytest-warnings`

---

## Why the warnings are harmless

After the `warnings.warn` fires at line 383 of `snowflake_connector.py`, the function does **not** return early. It falls through to process all name parts and still returns a joined string. The identifiers that trigger the warning are Airbyte internal staging tables (e.g. `AIRBYTE_SFTP_raw__stream_2025-03-23.csv`). Permifrost reads them back from `SHOW TABLES` for grant-comparison purposes only — it never generates `GRANT`/`REVOKE` statements targeting them. All real permission grants are unaffected.

**Why so many warnings?** Python deduplicates warnings by `(message_text, category, lineno)`. Because every Airbyte table name is distinct, every call produces a unique message text and all print.

---

## Files

| Action | Path |
|--------|------|
| Modify | `src/permifrost/snowflake_connector.py` (line 383) |
| Modify | `tests/permifrost/test_snowflake_connector.py` (lines 94–96) |

---

### Task 1: Update the failing test first (TDD red step)

**Files:**
- Modify: `tests/permifrost/test_snowflake_connector.py:94-96`

- [ ] **Step 1: Read the current test block**

```bash
grep -n "pytest.warns\|db16\|db17" tests/permifrost/test_snowflake_connector.py
```

Expected output shows lines ~94-96 with `pytest.warns(SyntaxWarning)`.

- [ ] **Step 2: Replace the `pytest.warns` assertion with a no-warning check**

Old code (lines 94–96):
```python
        with pytest.warns(SyntaxWarning):
            SnowflakeConnector.snowflaky(db16)
            SnowflakeConnector.snowflaky(db17)
```

New code:
```python
        import warnings as _warnings
        with _warnings.catch_warnings():
            _warnings.simplefilter("error")
            # These identifiers have periods in them but should not raise SyntaxWarning anymore
            SnowflakeConnector.snowflaky(db16)
            SnowflakeConnector.snowflaky(db17)
```

- [ ] **Step 3: Run the test to confirm it now FAILS (red)**

```bash
pytest tests/permifrost/test_snowflake_connector.py::TestSnowflakeConnector::test_snowflaky -v --disable-pytest-warnings
```

Expected: **FAILED** — `pytest.warns` is gone but the source still calls `warnings.warn`, which will raise inside `catch_warnings(simplefilter("error"))`.

---

### Task 2: Apply the fix (TDD green step)

**Files:**
- Modify: `src/permifrost/snowflake_connector.py:382-386`

- [ ] **Step 1: Open the file and locate the warning block**

Lines 381–386:
```python
        # We do not currently support identifiers that include periods (i.e. db_1.schema_1."table.with.period")
        if len(name_parts) > 3:
            warnings.warn(
                f"Unsupported object identifier: {name} contains additional periods within identifier.",
                SyntaxWarning,
            )
```

- [ ] **Step 2: Replace `warnings.warn` with `logger.debug`**

New code:
```python
        # We do not currently support identifiers that include periods (i.e. db_1.schema_1."table.with.period")
        if len(name_parts) > 3:
            logger.debug(
                "Unsupported object identifier: %s contains additional periods within identifier.",
                name,
            )
```

`logger` is already imported at line 15 (`from permifrost.logger import GLOBAL_LOGGER as logger`), so no new import is needed.

- [ ] **Step 3: Run the test to confirm it now PASSES (green)**

```bash
pytest tests/permifrost/test_snowflake_connector.py::TestSnowflakeConnector::test_snowflaky -v --disable-pytest-warnings
```

Expected: **PASSED**

- [ ] **Step 4: Run the full test suite**

```bash
pytest -x -v --disable-pytest-warnings
```

Expected: all tests pass, zero `SyntaxWarning` lines in output for multi-part identifiers.

- [ ] **Step 5: Verify `import warnings` can be removed if no longer needed**

```bash
grep -n "warnings\." src/permifrost/snowflake_connector.py
```

If only the null-identifier branch on line ~389 still uses `warnings.warn`, keep the import. If no other uses remain, remove the `import warnings` line.

- [ ] **Step 6: Commit**

```bash
git checkout -b fix/suppress-snowflaky-syntax-warnings
git add src/permifrost/snowflake_connector.py tests/permifrost/test_snowflake_connector.py
git commit -m "fix: replace SyntaxWarning flood in snowflaky() with logger.debug

Airbyte staging tables (e.g. AIRBYTE_SFTP_raw__stream_2025-03-23.csv)
have periods in their names, causing warnings.warn to fire once per
unique identifier. Switch to logger.debug so the messages are only
visible at DEBUG log level. Behaviour is unchanged — the function
still returns a value for these identifiers."
```

---

### Task 3: Manual smoke-test verification

- [ ] **Step 1: Confirm no warnings in normal output**

In a shell with the package installed, run permifrost in dry-run mode and pipe stderr through grep:

```bash
permifrost run --dry spec.yml 2>&1 | grep -i "syntaxwarning\|unsupported object"
```

Expected: **no output** (zero matching lines).

- [ ] **Step 2: Confirm messages appear at DEBUG level**

```bash
permifrost run --dry spec.yml 2>&1 | grep -i "unsupported object"
```

If the CLI supports `--log-level debug` or `LOGLEVEL=DEBUG`:
```bash
LOGLEVEL=DEBUG permifrost run --dry spec.yml 2>&1 | grep -i "unsupported object"
```

Expected: the debug lines appear, confirming the information is still accessible.

---

## Self-review checklist

- [x] Spec coverage: single requirement (suppress SyntaxWarning flood) → covered by Tasks 1 & 2.
- [x] No placeholders: all code blocks are complete and reference real lines/variables.
- [x] Type consistency: no new types introduced; `logger.debug` signature matches existing logger usage in the file.
- [x] The null-identifier `warnings.warn` (line ~389) is intentionally left as-is — that case indicates a genuine bug in the caller, not a known-harmless edge case.
