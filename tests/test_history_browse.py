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

    def test_mobile_shell_routes_include_consistent_nav(self):
        for path, active_label in (
            ("/auto", b"Auto"),
            ("/manual", b"Manual"),
            ("/history", b"History"),
        ):
            response = self.client.get(path)

            self.assertEqual(response.status_code, 200)
            self.assertIn(active_label, response.data)
            self.assertIn(b'href="/auto"', response.data)
            self.assertIn(b'href="/manual"', response.data)
            self.assertIn(b'href="/history"', response.data)
            self.assertNotIn(b"md:hidden", response.data)

    def test_auto_page_has_recording_controls(self):
        response = self.client.get("/auto")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Speech2Pictures - Auto", response.data)
        self.assertIn(b'id="pictureFrame"', response.data)
        self.assertIn(b'id="micToggleButton"', response.data)
        self.assertIn(b'id="micToggleIcon"', response.data)
        self.assertNotIn(b'id="startButton"', response.data)
        self.assertNotIn(b'id="stopButton"', response.data)
        self.assertIn(b'id="volumeMeter"', response.data)
        self.assertIn(b'id="transcriptHeading"', response.data)
        self.assertIn(b"Transcript (0%)", response.data)
        self.assertIn(b'id="transcriptText"', response.data)
        self.assertIn(b"No picture yet. Ready to record audio.", response.data)
        self.assertIn(b'id="statusText"', response.data)
        self.assertNotIn(b'id="serverMessage"', response.data)
        self.assertIn(b"/auto/generate", response.data)
        self.assertIn(b'href="/manual"', response.data)
        self.assertIn(b'href="/history"', response.data)
        self.assertIn(b"const autoTranscriptTargetChars = 200;", response.data)
        self.assertIn(
            b"window.SpeechRecognition || window.webkitSpeechRecognition",
            response.data,
        )
        self.assertIn(b"recognition.continuous = false", response.data)
        self.assertIn(b"recognition.interimResults = true", response.data)
        self.assertIn(b'recognition.lang = "en-US"', response.data)
        self.assertIn(b"recognition.addEventListener(\"start\"", response.data)
        self.assertIn(b"recognition.addEventListener(\"audiostart\"", response.data)
        self.assertIn(b"recognition.addEventListener(\"soundstart\"", response.data)
        self.assertIn(b"recognition.addEventListener(\"soundend\"", response.data)
        self.assertIn(b"recognition.addEventListener(\"speechstart\"", response.data)
        self.assertIn(b"recognition.addEventListener(\"speechend\"", response.data)
        self.assertIn(b"recognition.addEventListener(\"audioend\"", response.data)
        self.assertIn(b"recognition.addEventListener(\"nomatch\"", response.data)
        self.assertIn(b"recognition.addEventListener(\"error\"", response.data)
        self.assertIn(b"recognition.addEventListener(\"result\"", response.data)
        self.assertIn(b"describeSpeechError(event)", response.data)
        self.assertIn(b"not-allowed", response.data)
        self.assertIn(b"service-not-allowed", response.data)
        self.assertIn(b"setInterimTranscript(interimText)", response.data)
        self.assertIn(b"appendTranscript(finalText)", response.data)
        self.assertIn(b"recognition.start()", response.data)
        self.assertIn(b"recognition.stop()", response.data)
        self.assertIn(b"setMicButtonRecording(true)", response.data)
        self.assertIn(b"setMicButtonRecording(false)", response.data)
        self.assertIn(b"Starting speech recognition", response.data)
        self.assertIn(b"Open this page in Chrome to use Auto.", response.data)
        self.assertNotIn(b"/auto/transcribe", response.data)
        self.assertNotIn(b"STT diagnostics", response.data)
        self.assertNotIn(b'id="sttDiagnostics"', response.data)
        self.assertNotIn(b"window.speech2PicturesSttLog", response.data)
        self.assertNotIn(b"addSttDiagnostic(", response.data)
        self.assertNotIn(b"Open Manual", response.data)
        self.assertNotIn(b"MediaRecorder", response.data)
        self.assertNotIn(b"recordingSegment", response.data)
        self.assertNotIn(b"preferredRecorderMimeTypes", response.data)
        self.assertNotIn(b"enqueueSegmentUpload", response.data)
        self.assertNotIn(b"recorder.start(recordingChunkMs)", response.data)
        self.assertNotIn(b"getUserMedia", response.data)
        self.assertNotIn(b"getByteTimeDomainData", response.data)
        self.assertNotIn(b"createAnalyser", response.data)
        self.assertIn(
            b"transcriptBuffer.length / autoTranscriptTargetChars",
            response.data,
        )
        self.assertIn(b"appendTranscript(finalText)", response.data)
        self.assertIn(b"maybeGeneratePicture()", response.data)
        self.assertIn(b"JSON.stringify({transcript: transcriptSnapshot})", response.data)
        self.assertIn(b"renderGeneratedPicture(payload.picture)", response.data)
        self.assertIn(b"claimTranscriptForGeneration()", response.data)
        self.assertIn(b"transcriptSnapshot = transcriptBuffer.trim()", response.data)
        self.assertIn(b"generatePictureFromBuffer(true)", response.data)
        self.assertIn(b"generateAfterRecognitionEnd = true", response.data)
        self.assertIn(b"forceGenerateWhenReady", response.data)
        self.assertIn(b'transcriptBuffer = ""', response.data)
        self.assertNotIn(b"setInterval", response.data)
        self.assertNotIn(b"volume-pulse", response.data)

    def test_auto_page_shows_latest_image_metadata(self):
        self.add_record(
            "older transcript",
            "older title",
            "older style",
            "older description",
            "red",
        )
        latest_id = self.add_record(
            "latest transcript",
            "latest title",
            "latest style",
            "latest description",
            "green",
        )

        response = self.client.get("/auto")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"data:image/jpeg;base64", response.data)
        self.assertIn(b"latest title", response.data)
        self.assertIn(b"(latest style)", response.data)
        self.assertIn(b"Description", response.data)
        self.assertIn(b"Transcript", response.data)
        self.assertIn(b"metadata-popover", response.data)
        self.assertIn(b"metadata-popover-panel", response.data)
        self.assertIn(b"position: fixed", response.data)
        self.assertIn(b"left: 0.75rem", response.data)
        self.assertIn(b"right: 0.75rem", response.data)
        self.assertIn(b"bottom: calc(80px + 1rem)", response.data)
        self.assertIn(b"<details", response.data)
        self.assertIn(b"<summary", response.data)
        self.assertIn(b"latest description", response.data)
        self.assertIn(b"latest transcript", response.data)
        self.assertIn(b"[", response.data)
        self.assertNotIn(
            f'href="/history?ID={latest_id}"'.encode("utf-8"),
            response.data,
        )
        self.assertNotIn(("ID=" + str(latest_id)).encode("utf-8"), response.data)
        self.assertNotIn(("ID " + str(latest_id)).encode("utf-8"), response.data)
        self.assertNotIn(b"older title", response.data)

    def test_auto_generate_creates_saved_picture_from_transcript(self):
        generator = mock.Mock()
        generator.generate_title.return_value = (
            "generated title",
            "generated style",
            "generated description",
        )
        generator.generate_image.return_value = make_image("purple")
        self.app_module.get_image_generator = mock.Mock(return_value=generator)

        response = self.client.post(
            "/auto/generate",
            json={"transcript": "buffered conversation text"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["message"], "Picture generated.")
        picture = payload["picture"]
        self.assertEqual(picture["id"], 1)
        self.assertEqual(picture["transcript"], "buffered conversation text")
        self.assertEqual(picture["title"], "generated title")
        self.assertEqual(picture["style"], "generated style")
        self.assertEqual(picture["description"], "generated description")
        self.assertIn("timestamp", picture)
        self.assertNotEqual(picture["image"], "")

        generator.generate_title.assert_called_once_with(
            "buffered conversation text"
        )
        generator.generate_image.assert_called_once_with(
            "generated title",
            "generated style",
            "generated description",
        )

        saved = self.app_module.images_db.get_picture(1)
        self.assertIsNotNone(saved)
        transcript, title, style, description, _img = saved
        self.assertEqual(transcript, "buffered conversation text")
        self.assertEqual(title, "generated title")
        self.assertEqual(style, "generated style")
        self.assertEqual(description, "generated description")

    def test_auto_generate_requires_transcript_text(self):
        response = self.client.post("/auto/generate", json={"transcript": "  "})

        self.assertEqual(response.status_code, 400)
        payload = response.get_json()
        self.assertIn("No transcript", payload["message"])

    def test_auto_generate_reports_title_failure(self):
        generator = mock.Mock()
        generator.generate_title.return_value = ("", "", "")
        self.app_module.get_image_generator = mock.Mock(return_value=generator)

        response = self.client.post(
            "/auto/generate",
            json={"transcript": "buffered conversation text"},
        )

        self.assertEqual(response.status_code, 500)
        payload = response.get_json()
        self.assertIn("Could not generate a title", payload["message"])

    def test_auto_generate_reports_image_failure(self):
        generator = mock.Mock()
        generator.generate_title.return_value = (
            "generated title",
            "generated style",
            "generated description",
        )
        generator.generate_image.side_effect = RuntimeError("cuda unavailable")
        self.app_module.get_image_generator = mock.Mock(return_value=generator)

        response = self.client.post(
            "/auto/generate",
            json={"transcript": "buffered conversation text"},
        )

        self.assertEqual(response.status_code, 500)
        payload = response.get_json()
        self.assertIn("Image generation failed", payload["message"])
        self.assertIn("cuda unavailable", payload["message"])

    def test_mobile_history_uses_timestamp_only_metadata(self):
        image_id = self.add_record(
            "hidden transcript",
            "hidden title",
            "hidden style",
            "hidden description",
            "red",
        )

        response = self.client.get(f"/history?ID={image_id}")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Generated ", response.data)
        self.assertIn(b"data:image/jpeg;base64", response.data)
        self.assertNotIn(b"hidden transcript", response.data)
        self.assertNotIn(b"hidden title", response.data)
        self.assertNotIn(b"hidden style", response.data)
        self.assertNotIn(b"hidden description", response.data)


if __name__ == "__main__":
    unittest.main()
