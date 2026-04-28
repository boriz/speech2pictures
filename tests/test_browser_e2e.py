import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from urllib.error import URLError
from urllib.request import urlopen


RUN_BROWSER_TEST = (
    os.getenv("SPEECH2PICTURES_RUN_BROWSER_TEST", "").strip().lower()
    in {"1", "true", "yes"}
)


def _find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _wait_for_server(url, server, timeout=20):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if server.poll() is not None:
            output = ""
            if server.stdout is not None:
                output = server.stdout.read()
            raise RuntimeError(
                "Test server exited before becoming ready.\n" + output
            )
        try:
            with urlopen(url, timeout=1) as response:
                if response.status < 500:
                    return
        except URLError:
            pass
        time.sleep(0.2)
    output = ""
    if server.stdout is not None:
        output = server.stdout.read()
    raise RuntimeError(
        "Timed out waiting for test server at "
        + url
        + "\n"
        + output
    )


class BrowserE2eTests(unittest.TestCase):
    @unittest.skipUnless(
        RUN_BROWSER_TEST,
        "Set SPEECH2PICTURES_RUN_BROWSER_TEST=1 to run browser E2E test.",
    )
    def test_generate_and_browse_metadata(self):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            self.skipTest("Playwright is not installed: " + str(exc))

        repo_root = os.path.dirname(os.path.dirname(__file__))
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)

        db_path = os.path.join(temp_dir.name, "browser.sqlite")
        port = _find_free_port()
        base_url = f"http://127.0.0.1:{port}"
        server_script = os.path.join(repo_root, "tests", "browser_e2e_server.py")

        env = os.environ.copy()
        env["SPEECH2PICTURES_TEST_DB_FILE"] = db_path
        env["SPEECH2PICTURES_TEST_PORT"] = str(port)

        server = subprocess.Popen(
            [sys.executable, server_script],
            cwd=repo_root,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        self.addCleanup(self._stop_server, server)

        _wait_for_server(base_url + "/", server)

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                page = browser.new_page()

                page.goto(base_url + "/")
                self.assertIn("No images yet.", page.content())

                page.locator('input[name="Title"]').fill("Browser title 1")
                page.locator('input[name="Style"]').fill("Browser style 1")
                page.locator('textarea[name="Description"]').fill(
                    "Browser description 1"
                )
                page.get_by_role("button", name="Submit").click()

                page.wait_for_url("**/history/1")
                self.assertEqual(
                    page.locator('input[name="Title"]').input_value(),
                    "Browser title 1",
                )
                self.assertEqual(
                    page.locator('input[name="Style"]').input_value(),
                    "Browser style 1",
                )
                self.assertEqual(
                    page.locator('textarea[name="Description"]').input_value(),
                    "Browser description 1",
                )
                self.assertEqual(
                    page.locator('textarea[name="Transcript"]').input_value(),
                    "",
                )

                page.locator('textarea[name="Transcript"]').fill(
                    "spoken browser prompt"
                )
                page.locator('input[name="Title"]').fill("")
                page.locator('input[name="Style"]').fill("")
                page.locator('textarea[name="Description"]').fill("")
                page.get_by_role("button", name="Submit").click()

                page.wait_for_url("**/history/2")
                self.assertEqual(
                    page.locator('textarea[name="Transcript"]').input_value(),
                    "spoken browser prompt",
                )
                self.assertEqual(
                    page.locator('input[name="Title"]').input_value(),
                    "Generated from transcript",
                )
                self.assertEqual(
                    page.locator('input[name="Style"]').input_value(),
                    "browser test style",
                )
                self.assertIn(
                    "Browser test description for: spoken browser prompt",
                    page.locator('textarea[name="Description"]').input_value(),
                )

                page.get_by_role("button", name="Previous").click()
                page.wait_for_url("**/history/1")
                self.assertEqual(
                    page.locator('input[name="Title"]').input_value(),
                    "Browser title 1",
                )
                self.assertEqual(
                    page.locator('input[name="Style"]').input_value(),
                    "Browser style 1",
                )
                self.assertEqual(
                    page.locator('textarea[name="Description"]').input_value(),
                    "Browser description 1",
                )
                self.assertEqual(
                    page.locator('textarea[name="Transcript"]').input_value(),
                    "",
                )

                page.get_by_role("button", name="Next").click()
                page.wait_for_url("**/history/2")
                self.assertEqual(
                    page.locator('textarea[name="Transcript"]').input_value(),
                    "spoken browser prompt",
                )
                self.assertEqual(
                    page.locator('input[name="Title"]').input_value(),
                    "Generated from transcript",
                )
            finally:
                browser.close()

    def _stop_server(self, server):
        if server.poll() is not None:
            if server.stdout is not None:
                server.stdout.close()
            return
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=5)
        if server.stdout is not None:
            server.stdout.close()


if __name__ == "__main__":
    unittest.main()
