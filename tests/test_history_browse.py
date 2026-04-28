import importlib
import os
import sys
import tempfile
import unittest
from unittest import mock

from PIL import Image


def make_image(color):
    return Image.new("RGB", (8, 8), color=color)


def load_app_with_db(db_path):
    from config import config as app_config

    original_db_file_name = app_config.db_file_name
    app_config.db_file_name = db_path

    try:
        sys.modules.pop("app", None)
        app_module = importlib.import_module("app")
    finally:
        app_config.db_file_name = original_db_file_name

    return app_module


class HistoryBrowseUiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test.sqlite")
        self.app_module = load_app_with_db(self.db_path)
        self.client = self.app_module.app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def add_record(self, transcript, title, style, description, color):
        return self.app_module.images_db.add_picture(
            transcript,
            title,
            style,
            description,
            make_image(color),
        )

    def test_home_empty_state(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"No images yet.", response.data)
        self.assertIn(b"No image to display.", response.data)

    def test_missing_history_record(self):
        response = self.client.get("/history/999999")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"No image found for ID 999999.", response.data)
        self.assertIn(b"No image to display.", response.data)

    def test_previous_next_last_navigation(self):
        first_id = self.add_record("t1", "title 1", "style 1", "desc 1", "red")
        middle_id = self.add_record("t2", "title 2", "style 2", "desc 2", "green")
        last_id = self.add_record("t3", "title 3", "style 3", "desc 3", "blue")

        response = self.client.post(
            f"/history/{first_id}",
            data={"nav": "Previous"},
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], f"/history/{first_id}")

        response = self.client.post(
            f"/history/{middle_id}",
            data={"nav": "Previous"},
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], f"/history/{first_id}")

        response = self.client.post(
            f"/history/{middle_id}",
            data={"nav": "Next"},
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], f"/history/{last_id}")

        response = self.client.post(
            f"/history/{last_id}",
            data={"nav": "Next"},
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], f"/history/{last_id}")

        response = self.client.post(
            f"/history/{first_id}",
            data={"nav": "Last"},
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], f"/history/{last_id}")

    def test_browse_routes_do_not_instantiate_generator(self):
        guard = mock.Mock(side_effect=AssertionError("generator should not load"))
        self.app_module.get_image_generator = guard

        first_id = self.add_record("t1", "title 1", "style 1", "desc 1", "red")

        response = self.client.get("/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], f"/history/{first_id}")

        response = self.client.get(f"/history/{first_id}")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Current picture:", response.data)
        self.assertEqual(guard.call_count, 0)

    def test_history_page_shows_saved_prompt_fields(self):
        image_id = self.add_record(
            "saved transcript",
            "saved title",
            "saved style",
            "saved description",
            "red",
        )

        response = self.client.get(f"/history/{image_id}")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"saved transcript", response.data)
        self.assertIn(b'value="saved title"', response.data)
        self.assertIn(b'value="saved style"', response.data)
        self.assertIn(b"saved description", response.data)
        self.assertIn(
            b"Current picture: <br> saved title (saved style): saved description",
            response.data,
        )


if __name__ == "__main__":
    unittest.main()
