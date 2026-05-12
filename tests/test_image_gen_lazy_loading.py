import os
import tempfile
import types
import unittest
from unittest.mock import patch

from PIL import Image

import image_gen as image_gen_module
from config import config as app_config


def make_test_config():
    values = {
        key: value
        for key, value in vars(app_config).items()
        if not key.startswith("__")
    }
    return types.SimpleNamespace(**values)


class FakeModule:
    def __init__(self):
        self.to_calls = []

    def to(self, *args, **kwargs):
        self.to_calls.append((args, kwargs))
        return self


class FakeUnet(FakeModule):
    pass


class FakeScheduler:
    def __init__(self):
        self.config = {}


class FakePipe:
    def __init__(self):
        self.scheduler = FakeScheduler()
        self.unet = FakeUnet()
        self.device = "cpu"
        self.watermark = object()
        self.components = {
            "scheduler": self.scheduler,
            "unet": self.unet,
            "vae": FakeModule(),
            "text_encoder": FakeModule(),
            "text_encoder_2": FakeModule(),
            "tokenizer": FakeModule(),
            "tokenizer_2": FakeModule(),
        }

    @classmethod
    def from_pretrained(cls, *args, **kwargs):
        return cls()

    def to(self, device):
        self.device = device
        return self

    def enable_vae_slicing(self):
        return None

    def enable_vae_tiling(self):
        return None

    def enable_xformers_memory_efficient_attention(self):
        return None

    def enable_model_cpu_offload(self):
        return None

    def enable_sequential_cpu_offload(self):
        return None

    def enable_attention_slicing(self, *args, **kwargs):
        return None

    def __call__(self, *args, **kwargs):
        return types.SimpleNamespace(images=[Image.new("RGB", (8, 8))])


class FakeImg2ImgPipe(FakePipe):
    def __init__(self, **components):
        super().__init__()
        self.components = components


class ImageGenLazyLoadingTests(unittest.TestCase):
    def test_img2img_pipeline_loads_lazily(self):
        config = make_test_config()
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        source_image_path = os.path.join(temp_dir.name, "source.png")
        Image.new("RGB", (8, 8), color="white").save(source_image_path)

        with (
            patch.object(
                image_gen_module.StableDiffusionXLPipeline,
                "from_pretrained",
                side_effect=FakePipe.from_pretrained,
            ) as base_loader,
            patch.object(
                image_gen_module,
                "StableDiffusionXLImg2ImgPipeline",
                FakeImg2ImgPipe,
            ),
            patch.object(
                image_gen_module.DPMSolverMultistepScheduler,
                "from_config",
                return_value=FakeScheduler(),
            ),
            patch.object(
                image_gen_module.torch.cuda,
                "is_available",
                return_value=True,
            ),
        ):
            generator = image_gen_module.image_gen(config)

            self.assertEqual(base_loader.call_count, 0)
            self.assertIsNone(generator.pipe)
            self.assertIsNone(generator.img2img_pipe)

            image = generator.generate_image(
                "Title",
                "Style",
                "Description",
            )

            self.assertIsNotNone(image)
            self.assertEqual(base_loader.call_count, 1)
            self.assertIsNotNone(generator.pipe)
            self.assertIsNone(generator.pipe.watermark)
            self.assertIsNone(generator.img2img_pipe)

            image = generator.generate_image(
                "Title",
                "Style",
                "Description",
                source_image=source_image_path,
            )

            self.assertIsNotNone(image)
            self.assertEqual(base_loader.call_count, 1)
            self.assertIsNotNone(generator.img2img_pipe)

    def test_torch_compile_applies_only_to_text2img(self):
        config = make_test_config()
        with (
            patch.object(
                image_gen_module.StableDiffusionXLPipeline,
                "from_pretrained",
                side_effect=FakePipe.from_pretrained,
            ),
            patch.object(
                image_gen_module,
                "StableDiffusionXLImg2ImgPipeline",
                FakeImg2ImgPipe,
            ),
            patch.object(
                image_gen_module.DPMSolverMultistepScheduler,
                "from_config",
                return_value=FakeScheduler(),
            ),
            patch.object(
                image_gen_module.torch,
                "compile",
                side_effect=lambda unet, **kwargs: f"compiled:{unet}",
            ) as compile_mock,
            patch.object(
                image_gen_module.torch.cuda,
                "is_available",
                return_value=True,
            ),
            patch.object(
                config,
                "image_enable_torch_compile",
                True,
                create=True,
            ),
            patch.object(
                config,
                "image_enable_low_vram",
                False,
                create=True,
            ),
            patch.object(
                config,
                "image_enable_channels_last",
                True,
                create=True,
            ),
        ):
            generator = image_gen_module.image_gen(config)

            self.assertEqual(compile_mock.call_count, 0)
            self.assertFalse(generator._text2img_unet_compiled)
            self.assertFalse(generator._text2img_unet_channels_last)
            self.assertIsNone(generator.pipe)
            self.assertFalse(generator._using_xformers)

            generator.generate_image("Title", "Style", "Description")
            self.assertEqual(compile_mock.call_count, 1)
            self.assertTrue(generator._text2img_unet_compiled)
            self.assertTrue(generator._text2img_unet_channels_last)
            self.assertIsNone(generator.pipe.watermark)

            temp_dir = tempfile.TemporaryDirectory()
            self.addCleanup(temp_dir.cleanup)
            source_image_path = os.path.join(temp_dir.name, "source.png")
            Image.new("RGB", (8, 8), color="white").save(source_image_path)

            generator.generate_image(
                "Title",
                "Style",
                "Description",
                source_image=source_image_path,
            )

            self.assertEqual(compile_mock.call_count, 1)
            self.assertIsNotNone(generator.img2img_pipe)

    def test_channels_last_applies_to_unet_on_cuda(self):
        config = make_test_config()
        with (
            patch.object(
                image_gen_module.StableDiffusionXLPipeline,
                "from_pretrained",
                side_effect=FakePipe.from_pretrained,
            ),
            patch.object(
                image_gen_module,
                "StableDiffusionXLImg2ImgPipeline",
                FakeImg2ImgPipe,
            ),
            patch.object(
                image_gen_module.DPMSolverMultistepScheduler,
                "from_config",
                return_value=FakeScheduler(),
            ),
            patch.object(
                image_gen_module.torch.cuda,
                "is_available",
                return_value=True,
            ),
            patch.object(
                config,
                "image_enable_torch_compile",
                False,
                create=True,
            ),
            patch.object(
                config,
                "image_enable_low_vram",
                False,
                create=True,
            ),
            patch.object(
                config,
                "image_enable_channels_last",
                True,
                create=True,
            ),
        ):
            generator = image_gen_module.image_gen(config)

            self.assertFalse(generator._text2img_unet_channels_last)
            self.assertIsNone(generator.pipe)

            generator.generate_image("Title", "Style", "Description")

            self.assertTrue(generator._text2img_unet_channels_last)
            self.assertEqual(
                generator.pipe.unet.to_calls[-1][1]["memory_format"],
                image_gen_module.torch.channels_last,
            )

    def test_low_vram_mode_uses_attention_slicing_and_offload(self):
        config = make_test_config()
        with (
            patch.object(
                image_gen_module.StableDiffusionXLPipeline,
                "from_pretrained",
                side_effect=FakePipe.from_pretrained,
            ),
            patch.object(
                image_gen_module,
                "StableDiffusionXLImg2ImgPipeline",
                FakeImg2ImgPipe,
            ),
            patch.object(
                image_gen_module.DPMSolverMultistepScheduler,
                "from_config",
                return_value=FakeScheduler(),
            ),
            patch.object(
                image_gen_module.torch,
                "compile",
                side_effect=lambda unet, **kwargs: f"compiled:{unet}",
            ) as compile_mock,
            patch.object(
                image_gen_module.torch.cuda,
                "is_available",
                return_value=True,
            ),
            patch.object(
                config,
                "image_enable_low_vram",
                True,
                create=True,
            ),
            patch.object(
                config,
                "image_enable_torch_compile",
                True,
                create=True,
            ),
            patch.object(
                config,
                "image_enable_channels_last",
                True,
                create=True,
            ),
            patch.object(
                config,
                "image_enable_xformers",
                True,
                create=True,
            ),
        ):
            generator = image_gen_module.image_gen(config)

            self.assertTrue(generator.image_enable_low_vram)
            self.assertFalse(generator.image_enable_torch_compile)
            self.assertFalse(generator.image_enable_channels_last)
            self.assertTrue(generator.image_enable_xformers)
            self.assertFalse(generator._using_attention_slicing)
            self.assertFalse(generator._using_sequential_cpu_offload)
            self.assertFalse(generator._text2img_unet_compiled)
            self.assertFalse(generator._text2img_unet_channels_last)
            self.assertEqual(compile_mock.call_count, 0)
            self.assertIsNone(generator.pipe)

            generator.generate_image("Title", "Style", "Description")

            self.assertTrue(generator._using_sequential_cpu_offload)
            self.assertEqual(generator.pipe.unet.to_calls, [])
            self.assertIsNone(generator.pipe.watermark)

            temp_dir = tempfile.TemporaryDirectory()
            self.addCleanup(temp_dir.cleanup)
            source_image_path = os.path.join(temp_dir.name, "source.png")
            Image.new("RGB", (8, 8), color="white").save(source_image_path)

            generator.generate_image(
                "Title",
                "Style",
                "Description",
                source_image=source_image_path,
            )

            self.assertEqual(compile_mock.call_count, 0)
            self.assertIsNotNone(generator.img2img_pipe)


if __name__ == "__main__":
    unittest.main()
