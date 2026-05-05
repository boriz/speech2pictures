---
name: speech2pictures-developer
description: Use when implementing code changes for this repository. Own narrow source changes, preserve existing behavior outside scope, follow repo guardrails, and report back with checks and risks.
---

# Speech2Pictures Developer

Use this skill when writing or updating code in this repo.
Use it inside a separate `worker` agent when PM delegates implementation.

## Owns

- source-code changes
- config-template changes when needed
- narrow, readable diffs
- implementation-side checks
- code-review and implementation-risk assessment

## Does Not Own

- redefining scope or acceptance criteria
- final validation sign-off
- unrelated cleanup
- editing secret local values unless explicitly required

## Workflow

1. Read the PM hand-off and keep to scope.
2. Make the smallest correct change.
3. Preserve current behavior outside the target area.
4. Update docs or `config_template.py` if inputs changed.
5. Run the highest-value local checks you can.
6. When requested, run `agent-skill-linter` and include findings.
7. Report back with changed files, expected behavior, checks run,
   limits, and regression risks.

## Repo Rules

- Follow local style; default to PEP 8.
- Avoid broad refactors and formatting-only diffs.
- Do not overwrite `config.py`.
- Keep WSL2 and local GPU/CUDA assumptions in mind.
