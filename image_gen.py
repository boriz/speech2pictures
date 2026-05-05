import gc
import json
import logging
from contextlib import nullcontext
import warnings

import openai

import torch

from PIL import Image

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
        self.logger = logging.getLogger(__name__)
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
                self.logger.info(
                    "Disabling torch.compile because low-vram mode uses "
                    "sequential CPU offload."
                )
                self.image_enable_torch_compile = False
            if self.image_enable_channels_last:
                self.logger.info(
                    "Disabling channels_last because low-vram mode uses "
                    "sequential CPU offload."
                )
                self.image_enable_channels_last = False
            if self.image_enable_cpu_offload:
                self.logger.info(
                    "Ignoring model CPU offload because low-vram mode "
                    "uses sequential CPU offload instead."
                )
                self.image_enable_cpu_offload = False
            self.image_enable_sequential_cpu_offload = True

        if self.image_enable_torch_compile and self.image_enable_xformers:
            self.logger.info(
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
            self.logger.info("image_pipeline_xformers_enabled")
        except Exception as exc:
            self.logger.warning(
                "image_pipeline_xformers_unavailable error=%s",
                str(exc),
            )


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
            self.logger.warning("torch_compile_unavailable")
            return
        try:
            pipe.unet = torch.compile(
                pipe.unet,
                mode="reduce-overhead",
                fullgraph=True,
            )
            self._text2img_unet_compiled = True
            self.logger.info("torch_compile_enabled")
        except Exception as exc:
            self.logger.warning(
                "torch_compile_enable_failed error=%s",
                str(exc),
            )


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
            self.logger.info("channels_last_enabled")
        except Exception as exc:
            self.logger.warning(
                "channels_last_enable_failed error=%s",
                str(exc),
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
            self.logger.warning(
                "pipeline_release_to_cpu_failed error=%s",
                str(exc),
            )
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
                self.logger.warning(
                    "model_cpu_offload_unavailable error=%s",
                    str(exc),
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
                self.logger.info("sequential_cpu_offload_enabled")
            except Exception as exc:
                self.logger.warning(
                    "sequential_cpu_offload_unavailable error=%s",
                    str(exc),
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
        # The prompt is configured to return strict JSON; parsing below
        # intentionally fails hard for malformed responses.
        chat_completion = openai.ChatCompletion.create(
            model=self.gpt_model,
            messages=[{
                "role": "user",
                "content": self.gpt_prompt + transcript,
            }],
        )

        # Get the result
        response_text = chat_completion.choices[0].message.content
        self.logger.info(
            "title_generation_response_received chars=%s",
            len(response_text) if isinstance(response_text, str) else "n/a",
        )

        if not isinstance(response_text, str):
            raise ValueError(
                "Title generation response must be a JSON string; got "
                + type(response_text).__name__
            )

        try:
            payload = json.loads(response_text)
        except json.JSONDecodeError as exc:
            raise ValueError(
                "Title generation response is not valid JSON: " + str(exc)
            ) from exc

        if not isinstance(payload, dict):
            raise ValueError(
                "Title generation response must be a JSON object."
            )

        required_keys = {"title", "style", "description"}
        payload_keys = set(payload.keys())
        missing_keys = sorted(required_keys - payload_keys)
        unexpected_keys = sorted(payload_keys - required_keys)
        if missing_keys or unexpected_keys:
            raise ValueError(
                "Title generation response must contain exactly keys "
                + "title, style, description; missing="
                + str(missing_keys)
                + " unexpected="
                + str(unexpected_keys)
            )

        title = payload["title"]
        style = payload["style"]
        description = payload["description"]
        if not isinstance(title, str):
            raise ValueError(
                "Title generation field 'title' must be a string."
            )
        if not isinstance(style, str):
            raise ValueError(
                "Title generation field 'style' must be a string."
            )
        if not isinstance(description, str):
            raise ValueError(
                "Title generation field 'description' must be a string."
            )

        title_value = title.strip()
        if title_value == "":
            raise ValueError(
                "Title generation field 'title' must not be empty."
            )

        return title_value, style.strip(), description.strip()


    def generate_image(self, title, style, description, source_image = None):
        if self.device != "cuda":
            raise RuntimeError(
                "CUDA is not available. Image generation requires local "
                "GPU/CUDA; activate the project environment and verify the "
                "WSL CUDA driver setup."
            )

        # assemble the image prompt
        image_prompt = title + ". (" + style + "): " + description
        self.logger.info(
            "image_prompt_built title=%r style=%r prompt_chars=%s",
            title,
            style,
            len(image_prompt),
        )

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
