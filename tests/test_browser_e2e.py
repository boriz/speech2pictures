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

# Desktop target: FHD
DESKTOP_VIEWPORT = {"width": 1920, "height": 1080}
# Phone target: FHD+ equivalent in CSS pixels (Pixel 7 profile).
MOBILE_VIEWPORT = {"width": 412, "height": 915}
MOBILE_DPR = 2.625  # 412x915 @ 2.625 ~= 1080x2400
TEST_LOGIN_PASSWORD = "browser-password"


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
    def test_layout_and_gallery_popup_on_desktop_and_mobile(self):
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
        artifacts_dir = os.path.join(repo_root, "tests", "artifacts", "browser_e2e")
        os.makedirs(artifacts_dir, exist_ok=True)

        env = os.environ.copy()
        env["SPEECH2PICTURES_TEST_DB_FILE"] = db_path
        env["SPEECH2PICTURES_TEST_PORT"] = str(port)
        env["SPEECH2PICTURES_TEST_AUTH_PASSWORD"] = TEST_LOGIN_PASSWORD

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
                desktop_context = browser.new_context(viewport=DESKTOP_VIEWPORT)
                self._exercise_flow(
                    desktop_context.new_page(),
                    base_url,
                    os.path.join(artifacts_dir, "desktop"),
                )
                desktop_context.close()

                mobile_context = browser.new_context(
                    viewport=MOBILE_VIEWPORT,
                    device_scale_factor=MOBILE_DPR,
                    is_mobile=True,
                    has_touch=True,
                )
                self._exercise_flow(
                    mobile_context.new_page(),
                    base_url,
                    os.path.join(artifacts_dir, "mobile"),
                )
                mobile_context.close()
            finally:
                browser.close()

    def _exercise_flow(self, page, base_url, artifact_prefix):
        page.goto(base_url + "/")
        page.wait_for_url("**/login**")
        page.screenshot(path=artifact_prefix + "_login.png", full_page=True)
        page.locator('input[name="password"]').fill(TEST_LOGIN_PASSWORD)
        page.get_by_role("button", name="Sign In").click()
        page.wait_for_url("**/auto")
        page.wait_for_selector("#pictureFrame")
        page.screenshot(path=artifact_prefix + "_auto.png", full_page=True)
        self._assert_visible_in_viewport(page, ".mobile-shell-topbar")
        self._assert_visible_in_viewport(page, ".mobile-shell-nav")

        # Auto page should render a square image frame within the viewport.
        frame_box = page.locator("#pictureFrame").bounding_box()
        self.assertIsNotNone(frame_box)
        self.assertAlmostEqual(
            frame_box["width"],
            frame_box["height"],
            delta=8,
        )
        self.assertGreater(frame_box["width"], 100)

        # Seed one image through manual flow so History has gallery content.
        page.goto(base_url + "/manual")
        page.wait_for_selector("#manualPictureFrame")
        page.screenshot(path=artifact_prefix + "_manual.png", full_page=True)
        self._assert_visible_in_viewport(page, "#manualPictureFrame")
        page.locator('input[name="Title"]').fill("Browser title")
        page.locator('input[name="Style"]').fill("Browser style")
        page.locator('textarea[name="Description"]').fill("Browser description")
        page.get_by_role("button", name="Generate Image").click()
        page.wait_for_selector("#manualPictureFrame img")

        page.goto(base_url + "/history")
        page.wait_for_selector("[data-history-thumb]")
        page.screenshot(path=artifact_prefix + "_history_gallery.png", full_page=True)
        self._assert_visible_in_viewport(page, ".mobile-shell-topbar")
        self._assert_visible_in_viewport(page, ".mobile-shell-nav")
        self._assert_visible_in_viewport(page, "[data-history-thumb]")

        first_thumb = page.locator("[data-history-thumb]").first
        first_thumb.scroll_into_view_if_needed()
        scroll_before = page.evaluate("window.scrollY")
        first_thumb.click()
        page.wait_for_selector("#historyModal.flex")
        page.screenshot(path=artifact_prefix + "_history_modal.png", full_page=True)

        title_text = page.locator("#modalTitleStyle").inner_text().strip()
        self.assertNotEqual(title_text, "")

        # Closing the modal should not jump to a different page section.
        page.locator("#modalImage").click()
        page.wait_for_selector("#historyModal", state="hidden")
        scroll_after = page.evaluate("window.scrollY")
        self.assertLessEqual(abs(scroll_after - scroll_before), 5)

    def _assert_visible_in_viewport(self, page, selector):
        box = page.locator(selector).first.bounding_box()
        self.assertIsNotNone(box, f"Missing box for selector: {selector}")

        viewport = page.viewport_size
        self.assertIsNotNone(viewport)
        self.assertGreater(box["width"], 20, selector)
        self.assertGreater(box["height"], 20, selector)
        self.assertGreaterEqual(box["x"], -1, selector)
        self.assertGreaterEqual(box["y"], -1, selector)
        self.assertLessEqual(
            box["x"] + box["width"],
            viewport["width"] + 1,
            selector,
        )
        self.assertLessEqual(
            box["y"] + box["height"],
            viewport["height"] + 1,
            selector,
        )

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
