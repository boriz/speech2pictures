# Speech2Pictures

Speech2Pictures is a small Python application that turns text prompts
and speech transcripts into generated images.

This branch is focused on stabilizing the current Flask-based web app
before larger upgrades or feature expansion.

## Repo-Local Skills

Custom workflow skills for this repo live under:

- `repo-skills/speech2pictures-pm`
- `repo-skills/speech2pictures-developer`
- `repo-skills/speech2pictures-tester`

They are intentionally kept repo-local, not installed globally.

## Local Run Scripts

This repo includes two canonical shell helpers for the local WSL2
workflow, plus two deprecated legacy wrappers:

- `activate_venv.sh`: source this to activate the repo-local virtualenv
- `run_app.sh`: start the Flask app using the virtualenv tools directly
- `gunicorn.sh` and `ngrok_start.sh`: legacy wrappers kept as safe
  deprecation notices only

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

Fresh venv rebuild note:

- the pinned `openai-whisper` package can fail to build in a brand-new
  venv if `setuptools` is too new and `pkg_resources` is missing
- if that happens, install `setuptools<81` in the venv first, then
  install the Whisper package with `--no-build-isolation`

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

## WSL2 CUDA Troubleshooting

If image generation crashes in WSL2 with errors like:

- `Could not load library libcudnn_cnn_infer.so.8`
- `libcuda.so: cannot open shared object file: No such file or directory`

the WSL CUDA symlinks may be wrong or missing.

This repo includes a helper to repair the common symlink issue:

```bash
sudo ./fix_cuda.sh
```

What it does:

- replaces `/usr/lib/wsl/lib/libcuda.so.1.1`
- updates `/usr/lib/wsl/lib/libcuda.so`
- updates `/usr/lib/wsl/lib/libcuda.so.1`
- points all three names at the newest driver-provided
  `/usr/lib/wsl/drivers/*/libcuda.so.1.1`
- runs `ldconfig`

Notes:

- this is a system-level WSL fix, not a Python or app-level fix
- `sudo` is required because it modifies `/usr/lib/wsl/lib`
- you usually only need to run it when WSL CUDA is broken
- this only helps with the missing-library case; it does not replace a
  proper NVIDIA driver / WSL GPU setup

If CUDA is still broken after a Windows NVIDIA driver update or WSL
restart, NVIDIA's CUDA on WSL guide may need to be followed again:

- install the latest Windows NVIDIA driver
- run `wsl.exe --update`
- if Linux-side CUDA user-space packages need to be reinstalled, use the
  WSL-Ubuntu CUDA toolkit flow, not a Linux display driver inside WSL
- do not install the `cuda`, `cuda-12-x`, or `cuda-drivers`
  meta-packages inside WSL; install `cuda-toolkit-12-x` only

Reference:

- NVIDIA CUDA on WSL User Guide:
  https://docs.nvidia.com/cuda/wsl-user-guide/index.html

## Near-Term Priority

The immediate goal is to stabilize the current web app baseline:

- get the Flask app running reliably in its environment
- fix startup issues and broken routes/forms
- verify the basic generate-and-history flow
- defer dependency upgrades, model changes, and larger refactors until
  after the baseline is stable

## Testing Notes

Current automated coverage uses stdlib `unittest` plus Flask's test
client for route-level checks.

Current history/browse test command:

```bash
source ./activate_venv.sh
python3 -m unittest tests.test_history_browse
```

Optional browser E2E test:

```bash
source ./activate_venv.sh
python3 -m pip install playwright
python3 -m playwright install chromium
SPEECH2PICTURES_RUN_BROWSER_TEST=1 \
python3 -m unittest tests.test_browser_e2e
```

Optional image-generation timing test:

```bash
source ./activate_venv.sh
SPEECH2PICTURES_RUN_IMAGE_TIMING=1 \
python3 -m unittest tests.test_image_generation_timing
```

Current image runtime knobs in `config.py` / `config_template.py`:

- `image_width` / `image_height`
- `image_num_inference_steps`
- `image_enable_xformers`
- `image_enable_torch_compile`
- `image_enable_channels_last`
- `image_enable_cpu_offload`
- `image_enable_sequential_cpu_offload`
- `image_enable_low_vram`

Current SDXL stack notes:

- `diffusers` should stay at `0.19.3` or newer for SDXL support
- `torch.compile` is only applied to the hot `text2img` pipeline when
  the config flag is enabled and CUDA is available
- when `torch.compile` is enabled on this stack, the app disables
  `xformers` and relies on PyTorch 2.x SDPA instead
- on the current pinned `torch==2.0.1` stack, `torch.compile` is not a
  stable default for this app; keep it off unless the underlying torch
  stack is upgraded and re-benchmarked
- `image_enable_channels_last` forces the UNet into channels-last
  memory format on CUDA when the flag is enabled
- `image_enable_low_vram` switches the pipelines to sequential CPU
  offload, and it explicitly disables `torch.compile` and
  `channels_last` because that mode is about fitting memory, not
  squeezing the hot path
- `image_enable_sequential_cpu_offload` is the direct diffusers
  offload switch; `image_enable_low_vram` turns it on automatically
- if VRAM pressure remains high, first lower resolution / steps or
  enable CPU offload; if the issue persists in an isolated runtime,
  shared-memory / IPC tuning is only worth considering later

Measured RTX 3060 Ti profile from the rebuilt WSL2 venv:

- `768x768`, `16` steps, `image_enable_low_vram=True` completed in about
  `38.8s` generation time
- `768x768`, `16` steps, plain GPU mode with `channels_last=True`
  completed in about `42.7s` total generation time and started with
  almost no free VRAM, so it is not the recommended default on an
  8 GB card
- `512x512`, `16` steps, plain GPU mode with `channels_last=True`,
  `torch_compile=False`, and no offload completed in about `16.0s`
  generation time
- `image_enable_cpu_offload=True` hit a device-mismatch failure on the
  current pinned stack, so do not treat it as a stable profile yet

Recommended 8 GB local profile for now:

- `image_width = 512`
- `image_height = 512`
- `image_num_inference_steps = 16`
- `image_enable_xformers = False` unless it is installed and
  re-benchmarked locally
- `image_enable_torch_compile = False`
- `image_enable_channels_last = True`
- `image_enable_cpu_offload = False`
- `image_enable_sequential_cpu_offload = False`
- `image_enable_low_vram = False`
- use `image_enable_low_vram = True` only as the fallback profile when
  the plain GPU path runs out of memory

Future / TODO:

- expand Playwright browser coverage beyond the current generate/history
  smoke path into broader browse and future speech flows
- keep the browser suite separate from the current lightweight route-level
  `unittest` coverage
- evaluate a later upgrade from SDXL base to Stable Diffusion 3.5 once
  the runtime tradeoffs are acceptable for the target GPU setup
- treat `xformers` as an optional local optimization, not a tracked
  repo requirement; installing it can pull in a newer `torch`/`triton`
  stack that conflicts with the current `openai-whisper` pin
