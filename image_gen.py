import gc
from contextlib import nullcontext
import warnings

import openai
import re

import torch

from PIL import Image
from config import config

# accelerate imports pkg_resources internally on this pinned stack.
warnings.filterwarnings(
    "ignore",
    message="pkg_resources is deprecated as an API.*",
    category=UserWarning,
    module="accelerate\\.utils\\.torch_xla",
)

from diffusers import (
    DPMSolverMultistepScheduler,
    StableDiffusionXLImg2ImgPipeline,
    StableDiffusionXLPipeline,
)


class image_gen:

    def __init__(self, config):
        # Keep local variables
        self.gpt_prompt = config.gpt_prompt
        self.gpt_model = config.gpt_model
        self.image_model = getattr(
            config,
            "image_model",
            "stabilityai/stable-diffusion-xl-base-1.0",
        )
        self.image_width = getattr(config, "image_width", 1024)
        self.image_height = getattr(config, "image_height", 1024)
        self.image_num_inference_steps = getattr(
            config,
            "image_num_inference_steps",
            16,
        )
        self.image_enable_xformers = getattr(
            config,
            "image_enable_xformers",
            True,
        )
        self.image_enable_vae_slicing = getattr(
            config,
            "image_enable_vae_slicing",
            True,
        )
        self.image_enable_vae_tiling = getattr(
            config,
            "image_enable_vae_tiling",
            True,
        )
        self.image_enable_torch_compile = getattr(
            config,
            "image_enable_torch_compile",
            False,
        )
        self.image_enable_channels_last = getattr(
            config,
            "image_enable_channels_last",
            True,
        )
        self.image_enable_cpu_offload = getattr(
            config,
            "image_enable_cpu_offload",
            False,
        )
        self.image_enable_sequential_cpu_offload = getattr(
            config,
            "image_enable_sequential_cpu_offload",
            False,
        )
        self.image_enable_low_vram = getattr(
            config,
            "image_enable_low_vram",
            False,
        )
        openai.api_key = config.gpt_api_key

        if self.image_enable_low_vram:
            if self.image_enable_torch_compile:
                print(
                    "Disabling torch.compile because low-vram mode uses "
                    "sequential CPU offload."
                )
                self.image_enable_torch_compile = False
            if self.image_enable_channels_last:
                print(
                    "Disabling channels_last because low-vram mode uses "
                    "sequential CPU offload."
                )
                self.image_enable_channels_last = False
            if self.image_enable_cpu_offload:
                print(
                    "Ignoring model CPU offload because low-vram mode "
                    "uses sequential CPU offload instead."
                )
                self.image_enable_cpu_offload = False
            self.image_enable_sequential_cpu_offload = True

        if self.image_enable_torch_compile and self.image_enable_xformers:
            print(
                "Disabling xformers because torch.compile is enabled; "
                "this stack should use PyTorch SDPA instead."
            )
            self.image_enable_xformers = False

        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._using_xformers = False
        self._using_attention_slicing = False
        self._using_model_cpu_offload = False
        self._using_sequential_cpu_offload = False
        self._active_pipe_name = None
        self._text2img_unet_channels_last = False
        self._text2img_unet_compiled = False
        if self.device == "cuda":
            # Ampere GPUs can use TF32 for some kernels with little
            # quality impact and better throughput.
            torch.backends.cuda.matmul.allow_tf32 = True
            torch.backends.cudnn.allow_tf32 = True

        # Load image pipelines only when image generation is requested.
        self.pipe = None
        self.img2img_pipe = None


    def _configure_pipeline(self, pipe):
        if self.image_enable_vae_slicing:
            pipe.enable_vae_slicing()
        if self.image_enable_vae_tiling:
            pipe.enable_vae_tiling()
        if not self.image_enable_xformers:
            return
        try:
            pipe.enable_xformers_memory_efficient_attention()
            self._using_xformers = True
            print("Enabled xformers memory-efficient attention")
        except Exception as exc:
            print("xformers not available, continuing without it: " + str(exc))


    def _build_pipeline(self, pipeline_class):
        pipe = pipeline_class.from_pretrained(
            self.image_model,
            torch_dtype=torch.float16,
            variant="fp16",
            use_safetensors=True,
            add_watermarker=False,
        )
        pipe.scheduler = DPMSolverMultistepScheduler.from_config(
            pipe.scheduler.config
        )
        self._disable_watermark(pipe)
        self._configure_pipeline(pipe)
        return pipe


    def _build_img2img_pipeline(self):
        if self.img2img_pipe is not None:
            return self.img2img_pipe

        # Reuse the loaded SDXL components so img2img does not pull a
        # second full model copy into memory.
        self.img2img_pipe = StableDiffusionXLImg2ImgPipeline(
            **self.pipe.components,
            add_watermarker=False,
        )
        self._disable_watermark(self.img2img_pipe)
        self._configure_pipeline(self.img2img_pipe)
        return self.img2img_pipe


    def _disable_watermark(self, pipe):
        if hasattr(pipe, "watermark"):
            pipe.watermark = None


    def _maybe_compile_unet(self, pipe):
        if not self.image_enable_torch_compile or self.image_enable_low_vram:
            return
        if self.device != "cuda" or self.image_enable_cpu_offload:
            return
        if self._text2img_unet_compiled:
            return
        if not hasattr(torch, "compile"):
            print("torch.compile not available, continuing without it")
            return
        try:
            pipe.unet = torch.compile(
                pipe.unet,
                mode="reduce-overhead",
                fullgraph=True,
            )
            self._text2img_unet_compiled = True
            print("Enabled torch.compile on UNet")
        except Exception as exc:
            print("torch.compile not available, continuing without it: " + str(exc))


    def _maybe_enable_unet_channels_last(self, pipe):
        if not self.image_enable_channels_last or self.image_enable_low_vram:
            return
        if self.device != "cuda" or self.image_enable_cpu_offload:
            return
        if self._text2img_unet_channels_last:
            return
        try:
            pipe.unet = pipe.unet.to(memory_format=torch.channels_last)
            self._text2img_unet_channels_last = True
            print("Enabled channels_last memory format on UNet")
        except Exception as exc:
            print(
                "channels_last not available, continuing without it: "
                + str(exc)
            )


    def _pipe_for_name(self, pipeline_name):
        if pipeline_name == "text2img":
            return self.pipe
        if pipeline_name == "img2img":
            return self.img2img_pipe
        raise ValueError("Unknown pipeline name: " + str(pipeline_name))


    def _release_pipeline(self, pipe):
        if pipe is None or self.image_enable_cpu_offload:
            return
        try:
            pipe.to("cpu")
        except Exception as exc:
            print("Could not move pipeline to CPU: " + str(exc))
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()


    def _activate_pipeline(self, pipeline_name):
        pipe = self._pipe_for_name(pipeline_name)
        if pipe is None:
            if pipeline_name == "text2img":
                self.pipe = self._build_pipeline(StableDiffusionXLPipeline)
                pipe = self.pipe
            elif pipeline_name == "img2img":
                pipe = self._build_img2img_pipeline()
            else:
                raise ValueError("Unknown pipeline name: " + str(pipeline_name))

        if self.device != "cuda":
            self._active_pipe_name = pipeline_name
            return pipe

        if self.image_enable_cpu_offload:
            try:
                pipe.enable_model_cpu_offload()
                self._using_model_cpu_offload = True
            except Exception as exc:
                print(
                    "CPU offload not available, continuing without it: "
                    + str(exc)
                )
            self._active_pipe_name = pipeline_name
            return pipe

        if self._active_pipe_name == pipeline_name:
            return pipe

        if self._active_pipe_name is not None:
            self._release_pipeline(self._pipe_for_name(self._active_pipe_name))

        if self.image_enable_sequential_cpu_offload:
            try:
                pipe.enable_sequential_cpu_offload()
                self._using_sequential_cpu_offload = True
                print("Enabled sequential CPU offload for low-vram mode")
            except Exception as exc:
                print(
                    "Sequential CPU offload not available, continuing "
                    "without it: "
                    + str(exc)
                )
            self._active_pipe_name = pipeline_name
            return pipe

        pipe = pipe.to(self.device)
        self._maybe_enable_unet_channels_last(pipe)
        if pipeline_name == "text2img":
            self._maybe_compile_unet(pipe)
        if pipeline_name == "text2img":
            self.pipe = pipe
        else:
            self.img2img_pipe = pipe
        self._active_pipe_name = pipeline_name
        return pipe


    def _pipeline_kwargs(self):
        return {
            "width": self.image_width,
            "height": self.image_height,
            "num_inference_steps": self.image_num_inference_steps,
        }


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
            return "", "", ""

        return title, style, description


    def generate_image(self, title, style, description, source_image = None):
        if self.device != "cuda":
            raise RuntimeError(
                "CUDA is not available. Image generation requires local "
                "GPU/CUDA; activate the project environment and verify the "
                "WSL CUDA driver setup."
            )

        # assemble the image prompt
        image_prompt = title + ". (" + style + "): " + description
        print("========================================")
        print ("Image prompt: " + image_prompt)

        # Try to generate an image. If we have a source image, switch to img2img pipeline.
        pipeline_name = "img2img" if source_image is not None else "text2img"
        pipe = self._activate_pipeline(pipeline_name)

        inference_context = nullcontext
        if hasattr(torch, "inference_mode") and not self.image_enable_torch_compile:
            inference_context = torch.inference_mode
        elif hasattr(torch, "no_grad"):
            inference_context = torch.no_grad

        with inference_context():
            if source_image is not None:
                init_image = source_image
                if isinstance(source_image, str):
                    with Image.open(source_image) as opened_image:
                        init_image = opened_image.copy()
                elif not isinstance(source_image, Image.Image):
                    raise ValueError(
                        "source_image must be a PIL Image or a path to an image file"
                    )
                init_image = init_image.resize((self.image_width, self.image_height))
                img = pipe(
                    prompt=image_prompt,
                    image=init_image,
                    **self._pipeline_kwargs(),
                ).images[0]
            else:
                img = pipe(
                    image_prompt,
                    **self._pipeline_kwargs(),
                ).images[0]

        return img


if __name__ == "__main__":
    # Basci test code
    image_generator = image_gen(config)
    #title, style, description = image_generator.generate_title("Lets talk about white cow and how it can affect the car production")
    #print ("Image prompt: \n" + title + ". " + style + ". " + description)

    #img = image_generator.generate_image("Aloha Skies", "Pop Art", "This vibrant pop art piece captures the excitement of flying a hexacopter in Hawaii. It celebrates friendship, adventure, and the spirit of Hawaiian culture while reminding us to respect the environment.")
    img = image_generator.generate_image("Caricature", "Line Art", "Low-resolution monochrome caricature, make it look like the provided picture. Simplified line art, bold outlines. No color, no photorealism, no complex background, no fine textures", source_image="src.jpg")
    img.save("tmp.png")
