class config:
    energy_threshold = 1000
    microphone = "pulse"
    model_name = "medium"   # "tiny", "base", "small", "medium", "large"
    english_language = True
    phrase_timeout_sec = 30  # Phrase timeout
    image_refresh_sec = 300  # How often to refresh the picture
    gpt_api_key = "sk-<>"
    gpt_model = "gpt-3.5-turbo"
    gpt_prompt = "The following text is too long, make it shorter, less than 300 characters. Also, make the text sound like a painitng title. Source text: \n"    
    image_model = "stabilityai/stable-diffusion-2-1"
    
    