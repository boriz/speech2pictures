import openai
import torch
import config

from config import config
from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler



class image_gen:
    
    def __init__(self, config):
        # Keep local variables
        self.gpt_prompt = config.gpt_prompt
        self.gpt_model = config.gpt_model
        openai.api_key = config.gpt_api_key

        # Use the DPMSolverMultistepScheduler (DPM-Solver++) scheduler here instead
        self.pipe = StableDiffusionPipeline.from_pretrained(config.image_model, torch_dtype=torch.float16)
        self.pipe.scheduler = DPMSolverMultistepScheduler.from_config(self.pipe.scheduler.config)
        self.pipe = self.pipe.to("cuda")


    def generate_image(self, transcript):
        # create a chat completion        
        chat_completion = openai.ChatCompletion.create(model = self.gpt_model, messages=[{"role": "user", "content": self.gpt_prompt + transcript}])

        # print the chat completion
        picture_prompt = chat_completion.choices[0].message.content
        print("GPT picture name: " + picture_prompt)

        image = self.pipe(picture_prompt).images[0]
            
        return image



if __name__ == "__main__":
    image_generator = image_gen(config)
    image = image_generator.generate_image("Lets talk about white cow and how it can affect the car production")
    image.save("tmp.png")
