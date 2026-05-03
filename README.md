# Speech2Pictures

Speech2Pictures is a Flask web app for turning text and speech into
generated images.

The app stores generated images in SQLite and uses:

- OpenAI chat completions to turn transcript text into a structured prompt
- Stable Diffusion XL through Diffusers for image generation
- a local CUDA-capable GPU for image generation

## Web App

The intended web app has three tabs:

- **Auto**: browser microphone input is sent to the server, transcribed,
  converted into a prompt, and used to generate images automatically.
- **Manual**: the user enters transcript text or direct
  title/style/description fields and generates an image.
- **History**: the user browses previously generated images.

Both Auto and Manual should feed the same internal prompt shape:

- `title`
- `style`
- `description`

## Setup

Create `config.py` from `config_template.py` and fill in local values.
Do not commit real API keys or machine-specific secrets.

Install dependencies in a virtual environment:

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

Open:

```text
http://127.0.0.1:5055/manual
```

## Test

Compile the main Python files:

```bash
python3 -m py_compile app.py image_gen.py database.py speech2pic_cli.py
```

Run focused unit tests:

```bash
source ./activate_venv.sh
python3 -m unittest
```

Image generation, microphone input, and OpenAI calls require local
runtime configuration and may need separate manual checks.

## Configuration

Important image-generation settings live in `config.py` and are mirrored
in `config_template.py`:

- `image_model`
- `image_width`
- `image_height`
- `image_num_inference_steps`
- `image_enable_xformers`
- `image_enable_torch_compile`
- `image_enable_channels_last`
- `image_enable_cpu_offload`
- `image_enable_sequential_cpu_offload`
- `image_enable_low_vram`

For an 8 GB GPU, start with:

```python
image_width = 512
image_height = 512
image_num_inference_steps = 16
image_enable_xformers = False
image_enable_torch_compile = False
image_enable_channels_last = True
image_enable_cpu_offload = False
image_enable_sequential_cpu_offload = False
image_enable_low_vram = False
```

Use low-VRAM mode only if the normal GPU path runs out of memory.

## CUDA Notes

Diffusers image generation requires a working local CUDA setup.

In WSL2, errors such as these usually mean the CUDA driver libraries are
not visible inside WSL:

- `Could not load library libcudnn_cnn_infer.so.8`
- `libcuda.so: cannot open shared object file: No such file or directory`

This repo includes a helper for the common WSL symlink issue:

```bash
sudo ./fix_cuda.sh
```

That script updates `/usr/lib/wsl/lib/libcuda.so*` symlinks to point at
the newest driver-provided CUDA library under `/usr/lib/wsl/drivers/`
and runs `ldconfig`.

If CUDA is still unavailable, update the Windows NVIDIA driver and WSL
before changing Python dependencies.
