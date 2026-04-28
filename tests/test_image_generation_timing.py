import os
import tempfile
import time
import unittest
from contextlib import ExitStack
from unittest.mock import patch

import torch

from config import config as app_config
from image_gen import image_gen


RUN_TIMING_TEST = (
    os.getenv("SPEECH2PICTURES_RUN_IMAGE_TIMING", "").strip().lower()
    in {"1", "true", "yes"}
)


def _env_int(name, default):
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return int(value)


def _env_bool(name, default):
    value = os.getenv(name)
    if value is None or value == "":
        return default

    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False

    raise ValueError(
        f"Invalid boolean value for {name}: {value!r}"
    )


class ImageGenerationTimingTests(unittest.TestCase):
    @unittest.skipUnless(
        RUN_TIMING_TEST,
        "Set SPEECH2PICTURES_RUN_IMAGE_TIMING=1 to run timing test.",
    )
    def test_measure_image_generation_time(self):
        if not torch.cuda.is_available():
            self.skipTest("CUDA is not available in this environment.")

        width = _env_int(
            "SPEECH2PICTURES_TIMING_WIDTH",
            getattr(app_config, "image_width", 768),
        )
        height = _env_int(
            "SPEECH2PICTURES_TIMING_HEIGHT",
            getattr(app_config, "image_height", 768),
        )
        steps = _env_int(
            "SPEECH2PICTURES_TIMING_STEPS",
            getattr(app_config, "image_num_inference_steps", 20),
        )
        repeat = max(
            1,
            _env_int("SPEECH2PICTURES_TIMING_REPEAT", 2),
        )
        title = os.getenv("SPEECH2PICTURES_TIMING_TITLE", "portrait")
        style = os.getenv(
            "SPEECH2PICTURES_TIMING_STYLE",
            "abstract cartoon",
        )
        description = os.getenv(
            "SPEECH2PICTURES_TIMING_DESCRIPTION",
            "portrait of a cute cow",
        )
        low_vram = _env_bool(
            "SPEECH2PICTURES_TIMING_IMAGE_ENABLE_LOW_VRAM",
            getattr(app_config, "image_enable_low_vram", False),
        )
        xformers = _env_bool(
            "SPEECH2PICTURES_TIMING_IMAGE_ENABLE_XFORMERS",
            getattr(app_config, "image_enable_xformers", False),
        )
        torch_compile = _env_bool(
            "SPEECH2PICTURES_TIMING_IMAGE_ENABLE_TORCH_COMPILE",
            getattr(app_config, "image_enable_torch_compile", False),
        )
        channels_last = _env_bool(
            "SPEECH2PICTURES_TIMING_IMAGE_ENABLE_CHANNELS_LAST",
            getattr(app_config, "image_enable_channels_last", False),
        )
        cpu_offload = _env_bool(
            "SPEECH2PICTURES_TIMING_IMAGE_ENABLE_CPU_OFFLOAD",
            getattr(app_config, "image_enable_cpu_offload", False),
        )
        sequential_cpu_offload = _env_bool(
            "SPEECH2PICTURES_TIMING_IMAGE_ENABLE_SEQUENTIAL_CPU_OFFLOAD",
            getattr(
                app_config,
                "image_enable_sequential_cpu_offload",
                False,
            ),
        )

        torch.cuda.empty_cache()

        with ExitStack() as stack:
            stack.enter_context(
                patch.object(app_config, "image_width", width, create=True)
            )
            stack.enter_context(
                patch.object(app_config, "image_height", height, create=True)
            )
            stack.enter_context(
                patch.object(
                    app_config,
                    "image_num_inference_steps",
                    steps,
                    create=True,
                )
            )
            stack.enter_context(
                patch.object(
                    app_config,
                    "image_enable_low_vram",
                    low_vram,
                    create=True,
                )
            )
            stack.enter_context(
                patch.object(
                    app_config,
                    "image_enable_xformers",
                    xformers,
                    create=True,
                )
            )
            stack.enter_context(
                patch.object(
                    app_config,
                    "image_enable_torch_compile",
                    torch_compile,
                    create=True,
                )
            )
            stack.enter_context(
                patch.object(
                    app_config,
                    "image_enable_channels_last",
                    channels_last,
                    create=True,
                )
            )
            stack.enter_context(
                patch.object(
                    app_config,
                    "image_enable_cpu_offload",
                    cpu_offload,
                    create=True,
                )
            )
            stack.enter_context(
                patch.object(
                    app_config,
                    "image_enable_sequential_cpu_offload",
                    sequential_cpu_offload,
                    create=True,
                )
            )

            load_started = time.perf_counter()
            generator = image_gen(app_config)
            load_elapsed = time.perf_counter() - load_started

            gpu_name = torch.cuda.get_device_name(0)
            using_xformers = getattr(generator, "_using_xformers", False)
            using_low_vram = getattr(generator, "image_enable_low_vram", False)
            using_attention_slicing = getattr(
                generator,
                "_using_attention_slicing",
                False,
            )
            using_sequential_cpu_offload = getattr(
                generator,
                "_using_sequential_cpu_offload",
                False,
            )
            using_channels_last = getattr(
                generator,
                "_text2img_unet_channels_last",
                False,
            )
            using_torch_compile = getattr(
                generator,
                "image_enable_torch_compile",
                False,
            )
            using_model_cpu_offload = getattr(
                generator,
                "_using_model_cpu_offload",
                False,
            )
            mem_free, mem_total = torch.cuda.mem_get_info()

            print("=== Image Generation Timing ===")
            print(f"GPU: {gpu_name}")
            print(f"Resolution: {width}x{height}")
            print(f"Steps: {steps}")
            print(f"Repeats: {repeat}")
            print(f"low_vram: {using_low_vram}")
            print(f"xformers: {using_xformers}")
            print(f"attention_slicing: {using_attention_slicing}")
            print(
                "sequential_cpu_offload:"
                f" {using_sequential_cpu_offload}"
            )
            print(f"channels_last: {using_channels_last}")
            print(f"torch.compile: {using_torch_compile}")
            print(f"model_cpu_offload: {using_model_cpu_offload}")
            print(
                "CUDA memory before generation:"
                f" free={mem_free / (1024 ** 3):.2f} GiB"
                f" total={mem_total / (1024 ** 3):.2f} GiB"
            )
            print(f"Model load time: {load_elapsed:.2f}s")

            gen_times = []
            image = None
            for iteration in range(repeat):
                gen_started = time.perf_counter()
                try:
                    image = generator.generate_image(title, style, description)
                except Exception as exc:
                    gen_elapsed = time.perf_counter() - gen_started
                    allocated = torch.cuda.memory_allocated() / (1024 ** 3)
                    reserved = torch.cuda.memory_reserved() / (1024 ** 3)
                    self.fail(
                        "Image generation failed on iteration "
                        f"{iteration + 1}/{repeat} after {gen_elapsed:.2f}s "
                        f"with {type(exc).__name__}: {exc}\n"
                        f"CUDA allocated={allocated:.2f} GiB, "
                        f"reserved={reserved:.2f} GiB"
                    )

                gen_elapsed = time.perf_counter() - gen_started
                gen_times.append(gen_elapsed)
                print(
                    f"Generation {iteration + 1}/{repeat}: "
                    f"{gen_elapsed:.2f}s"
                )

            total_elapsed = load_elapsed + sum(gen_times)
            allocated = torch.cuda.memory_allocated() / (1024 ** 3)
            reserved = torch.cuda.memory_reserved() / (1024 ** 3)

            with tempfile.NamedTemporaryFile(
                suffix=".png",
                delete=False,
            ) as tmp_file:
                output_path = tmp_file.name
            image.save(output_path)

            print(f"First generation time: {gen_times[0]:.2f}s")
            if len(gen_times) > 1:
                print(f"Warm generation time: {gen_times[-1]:.2f}s")
            print(f"Total time including model load: {total_elapsed:.2f}s")
            print(
                "CUDA memory after generation:"
                f" allocated={allocated:.2f} GiB"
                f" reserved={reserved:.2f} GiB"
            )
            print(f"Saved output to: {output_path}")

            self.assertIsNotNone(image)


if __name__ == "__main__":
    unittest.main()
