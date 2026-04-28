import importlib
import os
import sys

from PIL import Image, ImageDraw

REPO_ROOT = os.path.dirname(os.path.dirname(__file__))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


def _require_env(name):
    value = os.getenv(name, "").strip()
    if value == "":
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


class FakeImageGenerator:
    def generate_title(self, transcript):
        transcript_value = transcript.strip()
        return (
            "Generated from transcript",
            "browser test style",
            "Browser test description for: " + transcript_value,
        )

    def generate_image(self, title, style, description, source_image=None):
        image = Image.new("RGB", (128, 128), color="#d6f0ff")
        draw = ImageDraw.Draw(image)
        draw.rectangle((8, 8, 120, 120), outline="#224466", width=3)
        draw.text((14, 18), title[:18], fill="#112233")
        draw.text((14, 48), style[:18], fill="#112233")
        draw.text((14, 78), description[:18], fill="#112233")
        return image


def main():
    db_path = _require_env("SPEECH2PICTURES_TEST_DB_FILE")
    port = int(os.getenv("SPEECH2PICTURES_TEST_PORT", "5055"))

    from config import config as app_config

    app_config.db_file_name = db_path
    sys.modules.pop("app", None)
    app_module = importlib.import_module("app")
    app_module.image_generator = FakeImageGenerator()

    app_module.app.run(
        host="127.0.0.1",
        port=port,
        debug=False,
        use_reloader=False,
    )


if __name__ == "__main__":
    main()
