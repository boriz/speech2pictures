# Speech2Pictures

Speech2Pictures is a Flask web app that turns transcript text into
generated images and stores results in SQLite.

## App Flow

The app has three tabs:

- **Auto**: listens in Chrome, builds transcript buffer, generates images.
- **Manual**: accepts transcript or direct title/style/description input.
- **History**: browses recently generated images.

## Current Behavior

### Auto Tab

- Works as an AI picture frame.
- User starts microphone in Chrome.
- Transcript text accumulates in a buffer.
- Transcript header shows progress as `Transcript (N%)`.
- When buffer reaches target size, image is generated and saved.
- Main frame shows latest image with `Title (Style)` and timestamp.
- Description and transcript are available in popup/tooltip UI.

### Manual Tab

- User can generate from either transcript text, or direct
  title/style/description fields.
- Generated image appears in the same shared frame style as Auto.
- Generation state is shown in-frame while waiting.

### History Tab

- Shows recent generated images.
- Clicking an image opens detail popup with title/style, description,
  transcript (if available), and timestamp.

## Setup

1. Copy `config_template.py` to `config.py` and fill in local values.
2. Install dependencies:

```bash
python3 -m venv venv
source ./activate_venv.sh
python3 -m pip install -r requirements.txt
```

## Run

```bash
source ./activate_venv.sh
python3 -m flask --app app run --host 127.0.0.1 --port 5055
```

Open `http://127.0.0.1:5055/auto`.

## Test

```bash
source ./activate_venv.sh
python3 -m unittest
```

## Linting

Python (Ruff):

```bash
./tools/run_python_lint.sh
./tools/run_python_lint.sh --fix
```

JavaScript in templates (ESLint + Prettier):

```bash
npm install --no-package-lock
./tools/run_js_lint.sh
./tools/run_js_lint.sh --fix
npm run format:js:check
```

Optional local gate commands before commit:

```bash
./tools/run_python_lint.sh && ./tools/run_js_lint.sh && source ./activate_venv.sh && python3 -m unittest tests.test_history_browse
```

## Configuration

Configuration variable details are documented inline in
`config_template.py` and `config.py` comments.

## Backlog

Planned and pending work is tracked in the [`todo/`](todo) folder.
