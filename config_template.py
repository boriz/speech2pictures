class config:
    # Login: hardcoded password list for simple session auth.
    auth_passwords = [
        "speech2pictures",
    ]
    auth_session_secret = "replace-with-a-long-random-string"

    # Auto tab: minimum transcript word count considered meaningful. Shorter
    # text can be discarded after a silence timeout because it is likely a
    # recognition glitch.
    auto_transcript_min_words = 3

    # Auto tab: if speech has ended and the transcript is shorter than the
    # minimum word count, discard it after this many seconds without more
    # speech.
    auto_silence_discard_seconds = 120

    # Auto tab: if speech has ended and the transcript is at least the minimum
    # word count, generate an image after this many seconds without more speech.
    auto_silence_generate_seconds = 60

    # Auto tab: hard cap for the transcript buffer. Generate immediately when
    # this many characters are captured, even if silence timeout has not fired.
    auto_transcript_max_chars = 700

    # History tab: number of newest images shown in the gallery.
    history_recent_limit = 50

    # Logging: rotating file logger settings.
    log_dir = "logs"
    log_file_name = "speech2pictures.log"
    log_level = "INFO"
    log_max_bytes = 5 * 1024 * 1024
    log_backup_count = 3

    # OpenAI: key + model for transcript -> title/style/description JSON.
    gpt_api_key = "sk-<>"
    gpt_model = "gpt-4o-mini"
    gpt_prompt = "You are a visual art AI. \
    You'll be provided with a transcript and you'll decide the painting style based on the transcript. \
    Reply with EXACTLY one JSON object and no extra text, markdown, or code fences. \
    The JSON object must contain exactly these string keys: title, style, description. \
    All values must be non-empty strings. \
    No additional keys. \
    Keep wording concrete and visual. \
    Total across all values should fit within 77 tokens. \
    Transcript: \n"

    # Image generation: SDXL model and performance/memory toggles.
    image_model = "stabilityai/stable-diffusion-xl-base-1.0"
    image_width = 512
    image_height = 512
    image_num_inference_steps = 16
    image_enable_xformers = False
    image_enable_vae_slicing = True
    image_enable_vae_tiling = True
    image_enable_torch_compile = False
    image_enable_channels_last = True
    image_enable_cpu_offload = False
    image_enable_sequential_cpu_offload = False
    image_enable_low_vram = False

    # SQLite file storing generated images + metadata.
    db_file_name = "image_database.sqlite"
