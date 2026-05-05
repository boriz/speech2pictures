import importlib
import os
import sys
import tempfile
import unittest
from unittest import mock

from PIL import Image

TEST_AUTH_PASSWORD = "test-password"


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
        self.app_module.config.auth_passwords = [TEST_AUTH_PASSWORD]
        self.client = self.app_module.app.test_client()
        self.authenticate_session()

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

    def authenticate_session(self):
        with self.client.session_transaction() as flask_session:
            flask_session["authenticated"] = True

    def clear_session_auth(self):
        with self.client.session_transaction() as flask_session:
            flask_session.clear()

    def test_protected_routes_redirect_to_login_when_not_authenticated(self):
        self.clear_session_auth()

        for path in ("/", "/auto", "/manual", "/history"):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 302)
            self.assertIn("/login?next=", response.headers["Location"])

    def test_valid_password_grants_access_and_honors_next_redirect(self):
        self.clear_session_auth()

        login_page = self.client.get("/login?next=/history")
        self.assertEqual(login_page.status_code, 200)

        response = self.client.post(
            "/login",
            data={"password": TEST_AUTH_PASSWORD, "next": "/history"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/history")

        follow_up = self.client.get("/history")
        self.assertEqual(follow_up.status_code, 200)
        self.assertIn(b"Speech2Pictures - History", follow_up.data)

    def test_invalid_password_stays_on_login_page(self):
        self.clear_session_auth()

        response = self.client.post(
            "/login",
            data={"password": "wrong-password", "next": "/auto"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Speech2Pictures - Login", response.data)
        self.assertIn(b"Invalid password.", response.data)
        protected_response = self.client.get("/auto")
        self.assertEqual(protected_response.status_code, 302)
        self.assertIn("/login?next=", protected_response.headers["Location"])

    def test_logout_clears_auth_session(self):
        response = self.client.get("/logout")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/login")

        follow_up = self.client.get("/auto")
        self.assertEqual(follow_up.status_code, 302)
        self.assertIn("/login?next=", follow_up.headers["Location"])

    def test_authenticated_login_route_redirects_to_auto(self):
        response = self.client.get("/login")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/auto")

    def test_login_page_contains_password_form(self):
        self.clear_session_auth()
        response = self.client.get("/login?next=/manual")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Speech2Pictures - Login", response.data)
        self.assertIn(b'name="password"', response.data)
        self.assertIn(b'name="next" value="/manual"', response.data)

    def test_home_routes_redirect_to_auto(self):
        response = self.client.get("/")
        index_response = self.client.get("/index.html")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/auto")
        self.assertEqual(index_response.status_code, 302)
        self.assertEqual(index_response.headers["Location"], "/auto")

    def test_missing_history_record(self):
        response = self.client.get("/history/999999")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"No images yet.", response.data)
        self.assertIn(b"Speech2Pictures - History", response.data)

    def test_legacy_history_id_route_opens_selected_image(self):
        first_id = self.add_record("t1", "title 1", "style 1", "desc 1", "red")
        second_id = self.add_record("t2", "title 2", "style 2", "desc 2", "green")

        response = self.client.get(f"/history/{first_id}")
        self.assertEqual(response.status_code, 200)
        self.assertIn(f"const selectedImageId = {first_id};".encode("utf-8"), response.data)

        response = self.client.get(f"/history/{second_id}")
        self.assertEqual(response.status_code, 200)
        self.assertIn(f"const selectedImageId = {second_id};".encode("utf-8"), response.data)

    def test_browse_routes_do_not_instantiate_generator(self):
        guard = mock.Mock(side_effect=AssertionError("generator should not load"))
        self.app_module.get_image_generator = guard

        first_id = self.add_record("t1", "title 1", "style 1", "desc 1", "red")

        response = self.client.get("/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/auto")

        response = self.client.get(f"/history/{first_id}")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Speech2Pictures - History", response.data)
        self.assertEqual(guard.call_count, 0)

    def test_history_page_shows_saved_prompt_metadata(self):
        image_id = self.add_record(
            "saved transcript",
            "saved title",
            "saved style",
            "saved description",
            "red",
        )

        response = self.client.get(f"/history/{image_id}")

        self.assertEqual(response.status_code, 200)
        self.assertIn(f'data-image-id="{image_id}"'.encode("utf-8"), response.data)
        self.assertIn(b"saved transcript", response.data)
        self.assertIn(b"saved title", response.data)
        self.assertIn(b"saved style", response.data)
        self.assertIn(b"saved description", response.data)
        self.assertIn(b"openHistoryModalFromButton", response.data)

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
            self.assertIn(b'href="/logout"', response.data)
            self.assertNotIn(b"md:hidden", response.data)
            self.assertIn(b"left-1/2", response.data)
            self.assertIn(b"max-w-2xl", response.data)
            self.assertIn(b"mobile-shell-topbar", response.data)
            self.assertIn(b"mobile-shell-topbar-title", response.data)
            self.assertIn(b"mobile-shell-topbar-action", response.data)

    def test_auto_page_has_recording_controls(self):
        response = self.client.get("/auto")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Speech2Pictures - Auto", response.data)
        self.assertIn(b'id="pictureFrame"', response.data)
        self.assertIn(b"shared-picture-section-fixed", response.data)
        self.assertIn(b"bottom-[72px]", response.data)
        self.assertIn(b"md:bottom-[76px]", response.data)
        self.assertIn(b"object-cover", response.data)
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
        configured_chars = getattr(
            self.app_module.config,
            "auto_transcript_target_chars",
            200,
        )
        self.assertIn(
            f"const autoTranscriptTargetChars = {int(configured_chars)};".encode("utf-8"),
            response.data,
        )
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
        self.assertIn(b"renderGeneratingFrame()", response.data)
        self.assertIn(b"restorePreviousFrame()", response.data)
        self.assertIn(b"Generating image...", response.data)
        self.assertIn(b"frame-spinner", response.data)
        self.assertIn(b'const clientLogEndpoint = "/client-log";', response.data)
        self.assertIn(b"sendClientLog(", response.data)
        self.assertIn(b"clientSessionId", response.data)
        self.assertIn(b"claimTranscriptForGeneration()", response.data)
        self.assertIn(b"transcriptSnapshot = transcriptBuffer.trim()", response.data)
        self.assertIn(b"generatePictureFromBuffer(true)", response.data)
        self.assertIn(b"generateAfterRecognitionEnd = true", response.data)
        self.assertIn(b"forceGenerateWhenReady", response.data)
        self.assertIn(b'transcriptBuffer = ""', response.data)
        self.assertIn(b'event.target.closest(".metadata-popover-panel")', response.data)
        self.assertIn(b'popoverPanel.closest("details")', response.data)
        self.assertNotIn(b"setInterval", response.data)
        self.assertNotIn(b"volume-pulse", response.data)

    def test_manual_page_has_shared_frame_and_generate_hooks(self):
        response = self.client.get("/manual")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Speech2Pictures - Manual", response.data)
        self.assertIn(b'id="manualPictureFrame"', response.data)
        self.assertIn(b"shared-picture-frame", response.data)
        self.assertIn(b"shared-picture-section-fixed", response.data)
        self.assertIn(b"Awaiting prompt...", response.data)
        self.assertIn(b'id="manualGenerateForm"', response.data)
        self.assertIn(b'id="manualGenerateButton"', response.data)
        self.assertIn(b'id="directControlsBlock"', response.data)
        self.assertIn(b"updateManualControlsState()", response.data)
        self.assertIn(b"renderManualGeneratingFrame()", response.data)
        self.assertIn(b"manualGenerateForm.dataset.submitting", response.data)
        self.assertIn(b"Generating image...", response.data)
        self.assertIn(b"frame-spinner", response.data)

    def test_client_log_endpoint_accepts_payload(self):
        response = self.client.post(
            "/client-log",
            json={
                "event": "stt_start",
                "level": "info",
                "message": "ok",
                "context": {"sessionId": "abc123"},
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["logged"])

    def test_client_log_endpoint_requires_event_name(self):
        response = self.client.post("/client-log", json={})

        self.assertEqual(response.status_code, 400)
        payload = response.get_json()
        self.assertIn("Missing event", payload["message"])

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
        self.assertIn(b"left: 50%;", response.data)
        self.assertIn(b"top: 50%;", response.data)
        self.assertIn(b"transform: translate(-50%, -50%)", response.data)
        self.assertIn(b"width: min(22rem, calc(100vw - 2.5rem))", response.data)
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

    def test_manual_generate_shows_image_and_clears_form_values(self):
        generator = mock.Mock()
        generator.generate_image.return_value = make_image("purple")
        self.app_module.get_image_generator = mock.Mock(return_value=generator)

        response = self.client.post(
            "/manual/txt2img",
            data={
                "Transcript": "",
                "Title": "manual title",
                "Style": "manual style",
                "Description": "manual description",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"data:image/jpeg;base64", response.data)
        self.assertNotIn(b"Generated 20", response.data)
        self.assertIn(b'id="manualPictureFrame"', response.data)
        self.assertIn(b'id="manualImageMetadataRow"', response.data)
        self.assertIn(b"manual title", response.data)
        self.assertIn(b"(manual style)", response.data)
        self.assertIn(b"Description", response.data)
        self.assertIn(
            b'id="title" name="Title" placeholder="Scene title..." type="text" value=""',
            response.data,
        )
        self.assertIn(
            b'id="style" name="Style" placeholder="e.g. Cinematic, Anime, Photoreal" type="text" value=""',
            response.data,
        )
        self.assertIn(
            b'id="description" name="Description" placeholder="Specific visual details..." rows="2"></textarea>',
            response.data,
        )
        self.assertIn(
            b'id="transcript" name="Transcript" placeholder="Paste dialogue or narrative here..." rows="3"></textarea>',
            response.data,
        )

    def test_mobile_history_shows_rich_metadata_with_conditional_transcript(self):
        image_id = self.add_record(
            "visible transcript",
            "visible title",
            "visible style",
            "visible description",
            "red",
        )

        response = self.client.get(f"/history?ID={image_id}")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"visible title", response.data)
        self.assertIn(b"visible style", response.data)
        self.assertIn(b"Description", response.data)
        self.assertIn(b"Transcript", response.data)
        self.assertIn(b"visible description", response.data)
        self.assertIn(b"visible transcript", response.data)
        self.assertIn(
            b'modalTitleStyle.textContent = `${title}${style ? ` (${style})` : ""}`.trim();',
            response.data,
        )
        self.assertIn(b"metadata-popover-panel", response.data)
        self.assertIn(b"aspect-square", response.data)
        self.assertIn(b"historyModal", response.data)
        self.assertIn(b"object-cover", response.data)
        self.assertIn(b"modalScrollAnchorY = window.scrollY", response.data)
        self.assertIn(b"window.scrollTo(0, modalScrollAnchorY)", response.data)
        self.assertIn(b"position: fixed", response.data)
        self.assertIn(b"left: 50%;", response.data)
        self.assertIn(b"top: 50%;", response.data)
        self.assertIn(b"[", response.data)
        self.assertIn(b"data:image/jpeg;base64", response.data)
        self.assertIn(
            f'data-image-id="{image_id}"'.encode("utf-8"),
            response.data,
        )
        self.assertNotIn(b"history-thumbnail-selected", response.data)
        self.assertIn(b"selectedButton.scrollIntoView({", response.data)
        self.assertIn(b'event.target.closest(".metadata-popover-panel")', response.data)

        no_transcript_id = self.add_record(
            "",
            "second title",
            "second style",
            "second description",
            "green",
        )
        response = self.client.get(f"/history?ID={no_transcript_id}")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"second title", response.data)
        self.assertIn(b"second style", response.data)
        self.assertIn(b"second description", response.data)
        self.assertNotIn(b"second transcript", response.data)
        self.assertIn(b'id="modalTranscriptDetails" class="metadata-popover hidden"', response.data)

    def test_mobile_history_only_loads_latest_fifty_records(self):
        for index in range(80):
            self.add_record(
                f"transcript {index}",
                f"title {index}",
                f"style {index}",
                f"description {index}",
                "red",
            )

        response = self.client.get("/history")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data.count(b'id="thumb-'), 50)
        self.assertIn(b"title 79", response.data)
        self.assertNotIn(b"title 29", response.data)

    def test_mobile_history_honors_configurable_recent_limit(self):
        for index in range(80):
            self.add_record(
                f"transcript {index}",
                f"title {index}",
                f"style {index}",
                f"description {index}",
                "red",
            )

        original_limit = getattr(
            self.app_module.config,
            "history_recent_limit",
            None,
        )
        self.app_module.config.history_recent_limit = 5
        try:
            response = self.client.get("/history")
        finally:
            if original_limit is None:
                delattr(self.app_module.config, "history_recent_limit")
            else:
                self.app_module.config.history_recent_limit = original_limit

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data.count(b'id="thumb-'), 5)

    def test_mobile_history_falls_back_to_default_limit_when_missing(self):
        for index in range(80):
            self.add_record(
                f"transcript {index}",
                f"title {index}",
                f"style {index}",
                f"description {index}",
                "red",
            )

        had_limit = hasattr(self.app_module.config, "history_recent_limit")
        original_limit = getattr(self.app_module.config, "history_recent_limit", None)
        if had_limit:
            delattr(self.app_module.config, "history_recent_limit")
        try:
            response = self.client.get("/history")
        finally:
            if had_limit:
                self.app_module.config.history_recent_limit = original_limit

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data.count(b'id="thumb-'), 50)


if __name__ == "__main__":
    unittest.main()
