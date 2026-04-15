# Speech2Pictures

Speech2Pictures is a small Python application that turns text prompts
and speech transcripts into generated images.

This branch is focused on stabilizing the current Flask-based web app
before larger upgrades or feature expansion.

## Local Run Scripts

This repo includes two small shell helpers for the local WSL2 workflow:

- `activate_venv.sh`: source this to activate the repo-local virtualenv
- `run_app.sh`: start the Flask app using the virtualenv tools directly

Examples:

```bash
source ./activate_venv.sh
python3 -m py_compile app.py image_gen.py database.py speech2pic_cli.py
```

```bash
./run_app.sh
```

By default, `run_app.sh` starts the app on `0.0.0.0:5000`.
You can override that with standard environment variables:

```bash
FLASK_RUN_HOST=127.0.0.1 FLASK_RUN_PORT=5001 ./run_app.sh
```

The current app still initializes the image pipeline during import, so
the first startup may require model availability in the local cache or
network access to Hugging Face.

## Current Branch Direction

The active product direction for this branch is:

- keep the existing Flask app as the main user interface
- stabilize the current manual image-generation flow first
- move the speech-driven experience into the web interface
- avoid large rewrites until the baseline app is working reliably

## Current App Shape

Today the repo contains two different interaction paths:

- `app.py`: the current Flask web app
- `speech2pic_cli.py`: an older microphone-driven CLI flow from the
  original `main` branch

The CLI file is still in the repo as legacy reference code. It is not
the intended long-term user experience for this branch.

## Intended Speech Feature

The speech-driven image flow should work through the web interface, not
through the legacy CLI.

Target behavior:

- the browser captures microphone audio
- the server receives audio and runs speech-to-text
- the transcript feeds the same prompt-processing pipeline used by text
  input
- the generated image appears in the web UI as part of a "photo frame"
  style experience

This keeps one backend-controlled transcription path and avoids
maintaining separate prompt-generation logic for web and CLI modes.

## Prompt Pipeline

The intended internal prompt format is:

- `title`
- `style`
- `description`

There are two planned ways to fill that structure:

- long-form text or speech transcript, which is converted into
  `title/style/description`
- direct manual entry of `title/style/description`

Both paths should converge on the same image-generation pipeline.

## UI Direction

The planned UI shape is a three-mode web interface:

- Gallery: browse generated images and open past items
- Generate: submit long text or direct prompt fields manually
- Photo Frame: microphone-driven speech input that updates the displayed
  image automatically

This separation is meant to keep the product understandable while
sharing the same backend pipeline.

## WSL2 Notes

This repository is being worked on inside WSL2.

That matters for the legacy CLI path in particular:

- `speech2pic_cli.py` contains Windows-specific behavior such as
  `mspaint.exe` and `taskkill.exe`
- that behavior reflects an older local workflow and should not be used
  as the target architecture for the web-based speech feature
- any future speech feature work should assume a browser-to-server flow
  that works cleanly from the web app instead of depending on local GUI
  programs
- the helper scripts above assume the Linux-side WSL2 checkout and the
  local `./venv` in this repo

## Near-Term Priority

The immediate goal is to stabilize the current web app baseline:

- get the Flask app running reliably in its environment
- fix startup issues and broken routes/forms
- verify the basic generate-and-history flow
- defer dependency upgrades, model changes, and larger refactors until
  after the baseline is stable
