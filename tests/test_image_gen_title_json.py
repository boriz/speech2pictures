import json
import types
import unittest
from unittest.mock import patch

import image_gen as image_gen_module
from config import config as app_config


def make_test_config():
    values = {
        key: value
        for key, value in vars(app_config).items()
        if not key.startswith("__")
    }
    return types.SimpleNamespace(**values)


def fake_chat_completion(content):
    return types.SimpleNamespace(
        choices=[types.SimpleNamespace(message=types.SimpleNamespace(content=content))]
    )


class ImageGenTitleJsonTests(unittest.TestCase):
    def make_generator(self):
        config = make_test_config()
        with patch.object(
            image_gen_module.torch.cuda,
            "is_available",
            return_value=False,
        ):
            return image_gen_module.image_gen(config)

    def test_generate_title_accepts_exact_json_object(self):
        generator = self.make_generator()
        payload = json.dumps(
            {
                "title": "Sunrise Street",
                "style": "Impressionism",
                "description": "Golden hour cityscape.",
            }
        )

        with patch.object(
            image_gen_module.openai.ChatCompletion,
            "create",
            return_value=fake_chat_completion(payload),
        ) as create_mock:
            title, style, description = generator.generate_title("transcript text")

        create_mock.assert_called_once()
        self.assertEqual(title, "Sunrise Street")
        self.assertEqual(style, "Impressionism")
        self.assertEqual(description, "Golden hour cityscape.")

    def test_generate_title_rejects_invalid_json(self):
        generator = self.make_generator()

        with patch.object(
            image_gen_module.openai.ChatCompletion,
            "create",
            return_value=fake_chat_completion("Title: hello"),
        ):
            with self.assertRaisesRegex(ValueError, "not valid JSON"):
                generator.generate_title("transcript text")

    def test_generate_title_rejects_missing_required_keys(self):
        generator = self.make_generator()
        payload = json.dumps(
            {
                "title": "Only title",
                "style": "No description",
            }
        )

        with patch.object(
            image_gen_module.openai.ChatCompletion,
            "create",
            return_value=fake_chat_completion(payload),
        ):
            with self.assertRaisesRegex(
                ValueError,
                "must contain exactly keys title, style, description",
            ):
                generator.generate_title("transcript text")

    def test_generate_title_rejects_empty_title(self):
        generator = self.make_generator()
        payload = json.dumps(
            {
                "title": "   ",
                "style": "Watercolor",
                "description": "A river scene.",
            }
        )

        with patch.object(
            image_gen_module.openai.ChatCompletion,
            "create",
            return_value=fake_chat_completion(payload),
        ):
            with self.assertRaisesRegex(ValueError, "must not be empty"):
                generator.generate_title("transcript text")


if __name__ == "__main__":
    unittest.main()
