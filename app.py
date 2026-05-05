import base64
import io
import logging
import os
import time
import uuid
from logging.handlers import RotatingFileHandler
from urllib.parse import urlsplit

from flask import (
    Flask,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)

from config import config
from database import database

app = Flask(__name__)
LOG_DIR_DEFAULT = "logs"
LOG_FILE_NAME_DEFAULT = "speech2pictures.log"
LOG_LEVEL_DEFAULT = "INFO"
LOG_MAX_BYTES_DEFAULT = 5 * 1024 * 1024
LOG_BACKUP_COUNT_DEFAULT = 3
AUTO_TRANSCRIPT_TARGET_CHARS_DEFAULT = 200
HISTORY_RECENT_LIMIT_DEFAULT = 50
AUTH_PASSWORDS_DEFAULT = ("speech2pictures",)
AUTH_SESSION_SECRET_DEFAULT = "speech2pictures-dev-session-secret"

image_generator = None


def _resolve_log_level(level_name):
    if not isinstance(level_name, str):
        return logging.INFO
    return getattr(logging, level_name.upper(), logging.INFO)


def _resolve_int_setting(value, default_value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default_value


def configure_logging():
    """Configure console + rotating file logging once per process."""
    log_dir = getattr(config, "log_dir", LOG_DIR_DEFAULT)
    log_file_name = getattr(config, "log_file_name", LOG_FILE_NAME_DEFAULT)
    log_level = _resolve_log_level(getattr(config, "log_level", LOG_LEVEL_DEFAULT))
    max_bytes = _resolve_int_setting(
        getattr(config, "log_max_bytes", LOG_MAX_BYTES_DEFAULT),
        LOG_MAX_BYTES_DEFAULT,
    )
    backup_count = _resolve_int_setting(
        getattr(config, "log_backup_count", LOG_BACKUP_COUNT_DEFAULT),
        LOG_BACKUP_COUNT_DEFAULT,
    )
    log_file_path = os.path.abspath(os.path.join(log_dir, log_file_name))

    os.makedirs(log_dir, exist_ok=True)

    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    has_console_handler = any(
        isinstance(handler, logging.StreamHandler)
        and not isinstance(handler, RotatingFileHandler)
        for handler in root_logger.handlers
    )
    if not has_console_handler:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    has_file_handler = False
    for handler in root_logger.handlers:
        if (
            isinstance(handler, RotatingFileHandler)
            and os.path.abspath(getattr(handler, "baseFilename", "")) == log_file_path
        ):
            handler.setLevel(log_level)
            handler.setFormatter(formatter)
            has_file_handler = True
            break

    if not has_file_handler:
        file_handler = RotatingFileHandler(
            log_file_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    app.logger.setLevel(log_level)
    app.logger.propagate = True
    return log_file_path


APP_LOG_FILE_PATH = configure_logging()
images_db = database(config)
app.logger.info("app_logging_ready log_file=%s", APP_LOG_FILE_PATH)
app.config["SECRET_KEY"] = getattr(
    config,
    "auth_session_secret",
    AUTH_SESSION_SECRET_DEFAULT,
)

AUTH_EXEMPT_ENDPOINTS = {
    "login",
    "logout",
    "favicon",
    "static",
}


def get_image_generator():
    global image_generator

    if image_generator is None:
        from image_gen import image_gen

        image_generator = image_gen(config)

    return image_generator


def _safe_request_id():
    return getattr(g, "request_id", "none")


def get_auth_passwords():
    configured_passwords = getattr(config, "auth_passwords", AUTH_PASSWORDS_DEFAULT)
    if isinstance(configured_passwords, str):
        candidates = [configured_passwords]
    elif isinstance(configured_passwords, (list, tuple, set)):
        candidates = list(configured_passwords)
    else:
        candidates = []

    passwords = []
    for value in candidates:
        password = str(value).strip()
        if password != "":
            passwords.append(password)
    return passwords


def is_session_authenticated():
    return session.get("authenticated") is True


def normalize_next_path(raw_next):
    next_path = str(raw_next or "").strip()
    if next_path == "":
        return ""

    parsed = urlsplit(next_path)
    if parsed.scheme or parsed.netloc:
        return ""
    if not next_path.startswith("/") or next_path.startswith("//"):
        return ""

    return next_path


def build_login_redirect():
    next_path = request.full_path
    if next_path.endswith("?"):
        next_path = next_path[:-1]
    return redirect(url_for("login", next=next_path))


@app.before_request
def before_request_logging():
    g.request_started_at = time.perf_counter()
    g.request_id = uuid.uuid4().hex[:12]


@app.before_request
def require_login():
    if request.endpoint is None:
        return None

    if request.endpoint in AUTH_EXEMPT_ENDPOINTS:
        return None

    if is_session_authenticated():
        return None

    return build_login_redirect()


@app.after_request
def after_request_logging(response):
    started_at = getattr(g, "request_started_at", None)
    elapsed_ms = 0.0
    if started_at is not None:
        elapsed_ms = (time.perf_counter() - started_at) * 1000.0

    response.headers["X-Request-ID"] = _safe_request_id()
    app.logger.info(
        "request_complete request_id=%s method=%s path=%s status=%s duration_ms=%.2f",
        _safe_request_id(),
        request.method,
        request.path,
        response.status_code,
        elapsed_ms,
    )
    return response


def render_manual_page(
    image_id=0,
    image=None,
    full_description="",
    message="",
    transcript="",
    title="",
    style="",
    description="",
    generated_at="",
    latest_image=None,
):
    return render_template(
        "manual.html",
        ID=image_id,
        Image=image,
        FullDescription=full_description,
        Message=message,
        TranscriptValue=transcript,
        TitleValue=title,
        StyleValue=style,
        DescriptionValue=description,
        GeneratedAt=generated_at,
        LatestImage=latest_image,
    )


def render_auto_page(message="Ready to record audio."):
    latest_image = None
    latest_id = images_db.get_last_picture_id()
    transcript_target_chars = getattr(
        config,
        "auto_transcript_target_chars",
        AUTO_TRANSCRIPT_TARGET_CHARS_DEFAULT,
    )

    if latest_id is not None:
        record = images_db.get_picture_with_timestamp(latest_id)
        if record is not None:
            transcript, title, style, description, img, timestamp = record
            latest_image = {
                "image": encode_image(img),
                "title": title,
                "style": style,
                "description": description,
                "transcript": transcript,
                "timestamp": timestamp,
            }

    return render_template(
        "auto.html",
        Message=message,
        LatestImage=latest_image,
        AutoTranscriptTargetChars=transcript_target_chars,
    )


def render_history_page(selected_id=None, message=""):
    records = images_db.get_recent_pictures(limit=get_history_recent_limit())
    images = []

    for image_id, timestamp, title, style, description, transcript, img in records:
        item = {
            "ID": image_id,
            "Timestamp": timestamp,
            "Title": title,
            "Style": style,
            "Description": description,
            "Transcript": transcript,
            "Image": encode_image(img),
        }
        images.append(item)

    if not images and message == "":
        message = "No images yet."

    selected_id_in_results = None
    if selected_id is not None:
        for item in images:
            if item["ID"] == selected_id:
                selected_id_in_results = selected_id
                break

    return render_template(
        "history.html",
        Images=images,
        SelectedID=selected_id_in_results,
        Message=message,
    )


def get_history_recent_limit():
    configured_limit = getattr(
        config,
        "history_recent_limit",
        HISTORY_RECENT_LIMIT_DEFAULT,
    )
    try:
        limit = int(configured_limit)
    except (TypeError, ValueError):
        return HISTORY_RECENT_LIMIT_DEFAULT

    if limit <= 0:
        return HISTORY_RECENT_LIMIT_DEFAULT

    return limit


def render_transcript_failure_page(
    transcript,
    title,
    style,
    description,
    page_renderer,
):
    return page_renderer(
        0,
        message="Could not generate a title from the transcript. "
        "Please edit the fields and try again.",
        transcript=transcript,
        title=title,
        style=style,
        description=description,
    )


def build_full_description(title, style, description):
    full_description = title
    if style:
        full_description = full_description + " (" + style + ")"
    if description:
        full_description = full_description + ": " + description
    return full_description


def encode_image(img):
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="JPEG")
    return base64.b64encode(img_bytes.getvalue()).decode("utf-8")


def build_auto_picture_payload(image_id):
    record = images_db.get_picture_with_timestamp(image_id)
    if record is None:
        return None

    transcript, title, style, description, img, timestamp = record
    return {
        "id": image_id,
        "timestamp": timestamp,
        "transcript": transcript,
        "title": title,
        "style": style,
        "description": description,
        "image": encode_image(img),
    }


def render_manual_success_page(image_id):
    record = images_db.get_picture_with_timestamp(image_id)
    if record is None:
        return render_manual_page(
            0,
            message="Generated image was saved, but could not be loaded.",
        )

    saved_transcript, title, style, description, img, timestamp = record
    encoded_image = encode_image(img)
    return render_manual_page(
        image_id,
        image=encoded_image,
        full_description=build_full_description(title, style, description),
        transcript="",
        title="",
        style="",
        description="",
        latest_image={
            "image": encoded_image,
            "title": title,
            "style": style,
            "description": description,
            "transcript": saved_transcript,
            "timestamp": timestamp,
        },
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    if is_session_authenticated():
        return redirect(url_for("auto"))

    next_path = normalize_next_path(
        request.values.get("next", request.args.get("next", "")),
    )
    message = ""
    if request.method == "POST":
        password = request.form.get("password", "")
        if password in get_auth_passwords():
            session["authenticated"] = True
            return redirect(next_path or url_for("auto"))
        message = "Invalid password."

    return render_template(
        "login.html",
        Message=message,
        NextPath=next_path,
    )


@app.route("/logout", methods=["GET", "POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@app.route("/index.html")
def home():
    return redirect(url_for("auto"))


@app.route("/auto")
def auto():
    app.logger.info(
        "auto_page_render request_id=%s log_file=%s",
        _safe_request_id(),
        APP_LOG_FILE_PATH,
    )
    return render_auto_page()


@app.route("/auto/generate", methods=["POST"])
def auto_generate():
    generate_started_at = time.perf_counter()
    payload = request.get_json(silent=True) or {}
    transcript = (
        payload.get("transcript")
        or request.form.get("transcript")
        or request.form.get("Transcript")
        or ""
    )
    transcript_value = transcript.strip()

    if transcript_value == "":
        app.logger.warning(
            "auto_generate_invalid_input request_id=%s reason=empty_transcript",
            _safe_request_id(),
        )
        return jsonify(
            {
                "message": "No transcript text was received.",
            }
        ), 400

    try:
        app.logger.info(
            "auto_generate_title_start request_id=%s transcript_chars=%s",
            _safe_request_id(),
            len(transcript_value),
        )
        title, style, description = get_image_generator().generate_title(
            transcript_value
        )
    except Exception as exc:
        app.logger.exception(
            "auto_generate_title_failed request_id=%s transcript_chars=%s error=%s",
            _safe_request_id(),
            len(transcript_value),
            str(exc),
        )
        return jsonify(
            {
                "message": "Could not generate a title from the transcript: "
                + str(exc),
            }
        ), 500

    title_value = title.strip()
    style_value = style.strip()
    description_value = description.strip()
    if title_value == "":
        app.logger.error(
            "auto_generate_title_empty request_id=%s transcript_chars=%s",
            _safe_request_id(),
            len(transcript_value),
        )
        return jsonify(
            {
                "message": "Could not generate a title from the transcript.",
            }
        ), 500

    try:
        app.logger.info(
            "auto_generate_image_start request_id=%s title=%r style=%r",
            _safe_request_id(),
            title_value,
            style_value,
        )
        img = get_image_generator().generate_image(
            title_value,
            style_value,
            description_value,
        )
        new_id = images_db.add_picture(
            transcript_value,
            title_value,
            style_value,
            description_value,
            img,
        )
    except Exception as exc:
        app.logger.exception(
            "auto_generate_image_failed request_id=%s title=%r error=%s",
            _safe_request_id(),
            title_value,
            str(exc),
        )
        return jsonify(
            {
                "message": "Image generation failed: " + str(exc),
            }
        ), 500

    picture = build_auto_picture_payload(new_id)
    if picture is None:
        app.logger.error(
            "auto_generate_missing_saved_image request_id=%s image_id=%s",
            _safe_request_id(),
            new_id,
        )
        return jsonify(
            {
                "message": "Generated image was saved, but could not be loaded.",
            }
        ), 500

    elapsed_ms = (time.perf_counter() - generate_started_at) * 1000.0
    app.logger.info(
        "auto_generate_success request_id=%s image_id=%s duration_ms=%.2f",
        _safe_request_id(),
        new_id,
        elapsed_ms,
    )
    return jsonify(
        {
            "message": "Picture generated.",
            "picture": picture,
        }
    )


@app.route("/manual")
def manual():
    app.logger.info("manual_page_render request_id=%s", _safe_request_id())
    return render_manual_page()


@app.route("/client-log", methods=["POST"])
def client_log():
    payload = request.get_json(silent=True) or {}
    event_name = str(payload.get("event") or "").strip()
    if event_name == "":
        return jsonify({"message": "Missing event name."}), 400

    level = str(payload.get("level") or "info").strip().lower()
    message = str(payload.get("message") or "").strip()
    context = payload.get("context")
    user_agent = request.headers.get("User-Agent", "")

    log_line = "client_event request_id=%s event=%s message=%r context=%r user_agent=%r"
    if level == "error":
        app.logger.error(
            log_line,
            _safe_request_id(),
            event_name,
            message,
            context,
            user_agent,
        )
    elif level == "warning":
        app.logger.warning(
            log_line,
            _safe_request_id(),
            event_name,
            message,
            context,
            user_agent,
        )
    else:
        app.logger.info(
            log_line,
            _safe_request_id(),
            event_name,
            message,
            context,
            user_agent,
        )

    return jsonify({"logged": True})


@app.route("/favicon.ico")
def favicon():
    return send_from_directory(
        os.path.join(app.root_path, "static"),
        "favicon.ico",
        mimetype="image/vnd.microsoft.icon",
    )


@app.route("/history")
def history_index():
    selected_id = request.args.get("ID", type=int)
    app.logger.info(
        "history_page_render request_id=%s selected_id=%s",
        _safe_request_id(),
        selected_id,
    )
    return render_history_page(selected_id)


@app.route("/history/<int:ID>", methods=["GET"])
def history(ID):
    app.logger.info(
        "history_view_image request_id=%s image_id=%s",
        _safe_request_id(),
        ID,
    )
    return render_history_page(selected_id=ID)


@app.route("/manual/txt2img", methods=["POST"])
def manual_txt2img():
    return handle_txt2img(
        render_manual_page,
        success_renderer=render_manual_success_page,
    )


def handle_txt2img(failure_renderer, success_renderer=None):
    transcript = request.form.get("Transcript", "")
    title = request.form.get("Title", "")
    style = request.form.get("Style", "")
    description = request.form.get("Description", "")

    transcript_value = transcript.strip()
    title_value = title.strip()
    style_value = style.strip()
    description_value = description.strip()

    if transcript_value != "":
        app.logger.info(
            "manual_generate_transcript_start request_id=%s transcript_chars=%s",
            _safe_request_id(),
            len(transcript_value),
        )
        try:
            generated_title, generated_style, generated_description = (
                get_image_generator().generate_title(transcript_value)
            )
        except Exception as exc:
            app.logger.exception(
                "manual_generate_title_failed request_id=%s error=%s",
                _safe_request_id(),
                str(exc),
            )
            return render_transcript_failure_page(
                transcript,
                title,
                style,
                description,
                failure_renderer,
            )

        if generated_title.strip() == "":
            return render_transcript_failure_page(
                transcript,
                title,
                style,
                description,
                failure_renderer,
            )

        title = generated_title
        style = generated_style
        description = generated_description
        title_value = title.strip()
        style_value = style.strip()
        description_value = description.strip()

    if title_value == "":
        app.logger.warning(
            "manual_generate_invalid_input request_id=%s reason=empty_title",
            _safe_request_id(),
        )
        return failure_renderer(
            0,
            message="Enter a title or transcript before generating an image.",
            transcript=transcript,
            title=title,
            style=style,
            description=description,
        )

    app.logger.info(
        "manual_generate_image_start request_id=%s title=%r style=%r",
        _safe_request_id(),
        title_value,
        style_value,
    )

    try:
        img = get_image_generator().generate_image(
            title_value,
            style_value,
            description_value,
        )
        new_id = images_db.add_picture(
            transcript_value,
            title_value,
            style_value,
            description_value,
            img,
        )
    except Exception as exc:
        app.logger.exception(
            "manual_generate_image_failed request_id=%s error=%s",
            _safe_request_id(),
            str(exc),
        )
        return failure_renderer(
            0,
            message="Image generation failed. Your form values were kept.",
            transcript=transcript,
            title=title,
            style=style,
            description=description,
        )

    app.logger.info(
        "manual_generate_success request_id=%s image_id=%s",
        _safe_request_id(),
        new_id,
    )
    if success_renderer is not None:
        return success_renderer(new_id)

    return redirect(url_for("history", ID=new_id))


if __name__ == "__main__":
    app.logger.info(
        "app_startup mode=direct log_file=%s",
        APP_LOG_FILE_PATH,
    )
    app.run(debug=True)
