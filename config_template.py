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
    You'll be provided with a transcript and you'll decide if it should be a photo or a painting based on the transcript. \
    Generate the follwoing fields: Title, Style, Description. \
    Description should be less than 300 characters. \
    Here is the transcript: \n"
    image_model = "stabilityai/stable-diffusion-2-1"
    db_file_name = "image_database.sqlite"
	