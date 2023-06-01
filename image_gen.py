import torch
from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler

model_id = "stabilityai/stable-diffusion-2-1"

# Use the DPMSolverMultistepScheduler (DPM-Solver++) scheduler here instead
pipe = StableDiffusionPipeline.from_pretrained(model_id, torch_dtype=torch.float16)
pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config)
pipe = pipe.to("cuda")

prompt = "Painful Secrecy: A Meeting Revealed - Davis and Tomlinson expose British government's cover-up in a delicate meeting discussing a deadly shipwreck."
image = pipe(prompt).images[0]
    
image.save("img_gen-01.png")

