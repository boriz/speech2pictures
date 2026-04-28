class config:
    energy_threshold = 1000
    microphone = "pulse"
    model_name = "medium"   # "tiny", "base", "small", "medium", "large"
    english_language = True
    phrase_timeout_sec = 30  # Phrase timeout
    image_refresh_sec = 120 #300  # How often to refresh the picture
    gpt_api_key = "sk-<>"
    gpt_model = "gpt-3.5-turbo"
    gpt_prompt = "You are a visual art AI. \
    You'll be provided with a transcript and you'll decide the painting style based on the transcript. \
    Generate the following fields: Title, Style, Description. \
    Description should be less than 300 characters. \
    Here is the transcript: \n"
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
    db_file_name = "image_database.sqlite"
	
