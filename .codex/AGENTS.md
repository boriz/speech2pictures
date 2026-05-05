# Codex Instructions

## Repo

Speech transcripts -> generated images.

- `app.py`: Flask UI
- `image_gen.py`: OpenAI + Diffusers
- `database.py`: SQLite
- `config.py`: local secrets, treat as local
- `config_template.py`: schema reference

## Rules

- Keep changes narrow.
- Do not touch unrelated local edits.
- Do not overwrite `config.py`.
- Never commit keys, tokens, or machine paths.
- If code needs new config, update `config_template.py` too.
- Preserve behavior unless task says otherwise.
- No broad refactors unless required.

## Python

- Follow local style, default to PEP 8.
- Avoid formatting-only diffs.
- Use 4 spaces, `snake_case`, short lines when practical.
- Keep imports grouped: stdlib, third-party, local.
- Add comments only when they help.

## Runtime

- OpenAI calls use `openai==0.27.7` style.
- Diffusers assumes local GPU/CUDA.
- Flask app and CLI read fields from `config.py`.
- App writes local files like `*.png` and
  `image_database.sqlite`.

## Validation

Start with:

- `python3 -m py_compile app.py image_gen.py database.py`
- targeted Flask route or CLI smoke checks when deps exist
- when requested, run the `agent-skill-linter` skill on the repo/skill
  targets and report actionable findings

Call out blockers: missing deps, GPU, mic, secrets.

## Roles

- PM: scope, acceptance, sequencing, risks, delegation
- Developer: code changes
- Tester: validation, regressions, defect reporting

## Routing

- PM stays in the main thread.
- Developer runs in a separate `worker` agent.
- Tester runs in a separate `worker` agent.
- For feature work, bugfixes, and any non-trivial code change:
  - PM delegates implementation to Developer.
  - PM then delegates validation to Tester.
  - PM does not combine Developer and Tester execution in one context.
- Main-thread direct coding is only for tiny non-code edits
  (for example wording/doc touch-ups) or when the user explicitly asks for
  a single-agent flow.
- Skills guide those workers, but workers provide the actual context
  isolation.
- PM dispatches work.
- Developer reports back to PM.
- PM sends tester work.
- After PM integrates a worker result, PM closes that completed worker agent
  before finalizing the next hand-off or user-facing summary.
- Developer and tester follow PM hand-offs unless the user overrides.
- Developer and tester must use `agent-skill-linter` when the task
  includes skill/agent protocol files or explicitly asks for linting.
- Review-only ownership:
  - PM: plans, process docs, branch/merge strategy, agent docs
  - Developer: code review, implementation risk
  - Tester: validation evidence, repros, regression review
- If a review spans types, PM splits it.

## Role Files

- PM: `.codex/agents/pm.md`
- Developer: `.codex/agents/developer.md`
- Tester: `.codex/agents/tester.md`
