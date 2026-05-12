---
name: javascript-lint-assistant
description: Lint inline JavaScript embedded in Jinja templates using ESLint with a safe autofix workflow.
---

# JavaScript Lint Assistant

Use this skill when you need lint/style checks for JavaScript in this repo.

## Styleguide

- Linter baseline: ESLint recommended rules.
- Formatter: Prettier.
- Style decisions:
  - Semicolons: on
  - Quotes: double quotes
  - Trailing commas: on (`es5`/Prettier default style)
  - Max line length: 88

## Commands

1. Install JS lint dependencies (first run only):
   `npm install --no-package-lock`
2. Lint report:
   `npm run lint:js`
3. Safe autofix pass:
   `npm run lint:js:fix`
4. Optional formatting checks:
   `npm run format:js:check`
   `npm run format:js`

Or run the wrapper:

- Check only: `./tools/run_js_lint.sh`
- Autofix + recheck: `./tools/run_js_lint.sh --fix`

## Template-specific behavior

`tools/lint_js_templates.mjs` extracts inline `<script>` blocks from
`templates/**/*.html`, sanitizes Jinja placeholders, and lints the
generated JS so ESLint can run reliably on this codebase.

