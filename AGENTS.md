# Codex Instructions

## Repo

Speech transcripts -> generated images.

- `app.py`: Flask UI
- `speech2pic_cli.py`: old mic CLI
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

- `python3 -m py_compile app.py image_gen.py database.py speech2pic_cli.py`
- targeted Flask route or CLI smoke checks when deps exist

Call out blockers: missing deps, GPU, mic, secrets.

## Roles

- PM: scope, acceptance, sequencing, risks, delegation
- Developer: code changes
- Tester: validation, regressions, defect reporting

## Routing

- PM dispatches work.
- PM may start developer and tester agents as needed.
- Developer reports back to PM.
- PM sends tester work.
- Developer and tester follow PM hand-offs unless the user overrides.
- Review-only ownership:
  - PM: plans, process docs, branch/merge strategy, agent docs
  - Developer: code review, implementation risk
  - Tester: validation evidence, repros, regression review
- If a review spans types, PM splits it.

## Role Files

- PM: `.codex/agents/pm.md`
- Developer: `.codex/agents/developer.md`
- Tester: `.codex/agents/tester.md`
