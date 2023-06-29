import openai
import torch
import re
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


    def generate_title(self, transcript):
        # create a chat completion 
        #print("GPT prompt: \n" + self.gpt_prompt + transcript)

        try:
            chat_completion = openai.ChatCompletion.create(model = self.gpt_model, messages=[{"role": "user", "content": self.gpt_prompt + transcript}])

            # Get the result      
            res = chat_completion.choices[0].message.content

            print("========================================")            
            print("Form GPT: \n" + res)

            # Be sure that we've got a legit reply
            title = re.search("Title: (.+?)\n", res).group(1)
            # ChatGPT sometimes adds extra quotes, remove them
            title = title.replace('"', '')
            style = re.search("Style: (.*?)\n", res).group(1)
            description = re.search("Description: (.*?)(\n|$)", res).group(1)
        except Exception as e:
            print("Got exception from ChatGPT: " + str(e))
            return None, None, None, None
            
        return title, style, description
    

    def generate_image(self, title, style, description):
        # assemble the image prompt
        image_prompt = title + ". (" + style + "): " + description
        print("========================================")
        print ("Image prompt: " + image_prompt)

        # Try to generate an image
        img = self.pipe(image_prompt).images[0]
            
        return img


if __name__ == "__main__":
    # Basci test code
    image_generator = image_gen(config)
    #title, style, description = image_generator.generate_title("Lets talk about white cow and how it can affect the car production")
    #print ("Image prompt: \n" + title + ". " + style + ". " + description)

    img = image_generator.generate_image("Aloha Skies", "Pop Art", "This vibrant pop art piece captures the excitement of flying a hexacopter in Hawaii. It celebrates friendship, adventure, and the spirit of Hawaiian culture while reminding us to respect the environment.")
    
    img.save("tmp.png")
