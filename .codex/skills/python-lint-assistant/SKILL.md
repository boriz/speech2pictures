---
name: python-lint-assistant
description: Run and triage Ruff lint for this repo with a safe autofix path, then verify clean results.
---

# Python Lint Assistant

Use this skill when you need Python lint/style guidance for Speech2Pictures.

## Styleguide

- Baseline: PEP 8.
- Linter: Ruff.
- Enabled rule groups: `E`, `W`, `F`, `I`, `B`, `UP`.

## Commands

1. Baseline report:
   `source ./activate_venv.sh && python3 -m ruff check .`
2. Safe autofix pass:
   `source ./activate_venv.sh && python3 -m ruff check --fix .`
3. Formatter pass:
   `source ./activate_venv.sh && python3 -m ruff format .`
4. Re-check:
   `source ./activate_venv.sh && python3 -m ruff check .`

Or run the wrapper:

- Check only: `./tools/run_python_lint.sh`
- Autofix + recheck: `./tools/run_python_lint.sh --fix`

## Triage Guidance

- Prioritize correctness-risk findings (`B`, syntax, undefined names) first.
- Apply smallest behavioral-safe fix.
- Re-run lint after each fix batch.

