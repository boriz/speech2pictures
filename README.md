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
- User starts microphone in Chrome. Auto uses browser speech recognition, so
  Chrome is required for live speech capture.
- Transcript text accumulates in a buffer.
- Transcript header shows word count as `Transcript: 58 words (3 min)`.
- After speech pauses, meaningful transcripts generate after the configured
  timeout; short transcripts are discarded after their configured timeout.
- Reaching the configured transcript character limit generates immediately.
- Main frame shows latest image with `Title (Style)` and timestamp.
- Description and transcript are available as frame overlays.

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

1. Copy `config_template.py` to `config.py` and fill in local values:
   `auth_passwords`, `auth_session_secret`, OpenAI settings, image settings,
   and database/log paths as needed.
2. Install dependencies:

```bash
python3 -m venv venv
source ./activate_venv.sh
python3 -m pip install -r requirements.txt
```

## Run

Normal local run:

```bash
./run_app.sh
```

By default this serves `http://0.0.0.0:5000/auto`. Override host or port with
`FLASK_RUN_HOST` and `FLASK_RUN_PORT`.

Direct Flask run, useful when you want a specific localhost port:

```bash
source ./activate_venv.sh
python3 -m flask --app app run --host 127.0.0.1 --port 5055
```

Open `http://127.0.0.1:5055/auto`.

## ngrok

Use the template for local ngrok exposure:

```bash
cp ngrok_s2p.sh.template ngrok_s2p.sh
```

Edit `DOMAIN` in `ngrok_s2p.sh`, then run:

```bash
./ngrok_s2p.sh
```

The script maps ngrok to port `5000` with `ngrok http --url=... 5000` and then
starts the app through `./run_app.sh`.

## Test

```bash
source ./activate_venv.sh
python3 -m unittest
```

Optional browser E2E test:

```bash
SPEECH2PICTURES_RUN_BROWSER_TEST=1 python3 -m unittest tests.test_browser_e2e
```

This requires Playwright and browser dependencies.

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
`config_template.py` and `config.py` comments. Common values to tune:

- Auto transcript behavior: `auto_transcript_min_words`,
  `auto_silence_discard_seconds`, `auto_silence_generate_seconds`,
  `auto_transcript_max_chars`.
- History size: `history_recent_limit`.
- Image generation: `image_width`, `image_height`,
  `image_num_inference_steps`, and memory/performance toggles such as
  `image_enable_low_vram`, `image_enable_xformers`,
  `image_enable_torch_compile`, and CPU offload settings.
- Authentication: `auth_passwords` and `auth_session_secret`.

## Backlog

Planned and pending work is tracked in the [`todo/`](todo) folder.
