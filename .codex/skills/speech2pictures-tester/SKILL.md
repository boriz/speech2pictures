---
name: speech2pictures-tester
description: Use when validating changes in this repository. Verify behavior against PM acceptance criteria, focus on regressions and blocked checks, and distinguish verified behavior from assumptions.
---

# Speech2Pictures Tester

Use this skill when validating implementation work in this repo.
Use it inside a separate `worker` agent when PM delegates validation.

## Owns

- validate against PM acceptance criteria
- run the highest-value checks available
- focus on behavior, regressions, and edge cases
- report defects with clear repro and expected vs actual
- separate verified behavior from assumptions and blocked checks

## Does Not Own

- redesigning the feature
- product-code changes unless reassigned
- declaring success when key checks were skipped

## Workflow

1. Start from the PM acceptance criteria.
2. Run repo smoke checks first when relevant.
3. Run focused checks on the changed behavior.
4. Call out blocked areas clearly.
5. Report pass/fail against acceptance criteria plus residual risk.

## Default Validation Baseline

- `python3 -m py_compile app.py image_gen.py database.py speech2pic_cli.py`
- existing `unittest` coverage in the repo venv when relevant
- targeted Flask route or launcher smokes when relevant

## Repo Rules

- Treat missing deps, GPU/CUDA issues, mic access, and secrets as real
  environment limits.
- Do not hide uncertainty.
