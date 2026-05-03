class config:
    auto_transcript_target_chars = 200
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
	
