import os
import io
import base64

from flask import (
    Flask,
    jsonify,
    render_template,
    request,
    redirect,
    url_for,
    send_from_directory,
)

from config import config
from database import database


app = Flask(__name__)

image_generator = None
images_db = database(config)
AUTO_TRANSCRIPT_TARGET_CHARS_DEFAULT = 200


def get_image_generator():
    global image_generator

    if image_generator is None:
        from image_gen import image_gen

        image_generator = image_gen(config)

    return image_generator


def render_image_page(
    image_id,
    image=None,
    full_description="",
    message="",
    transcript="",
    title="",
    style="",
    description="",
):
    return render_template(
        'index.html',
        ID=image_id,
        Image=image,
        FullDescription=full_description,
        Message=message,
        TranscriptValue=transcript,
        TitleValue=title,
        StyleValue=style,
        DescriptionValue=description,
    )


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
):
    return render_template(
        'mobile_manual.html',
        ID=image_id,
        Image=image,
        FullDescription=full_description,
        Message=message,
        TranscriptValue=transcript,
        TitleValue=title,
        StyleValue=style,
        DescriptionValue=description,
        GeneratedAt=generated_at,
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
        'mobile_auto.html',
        Message=message,
        LatestImage=latest_image,
        AutoTranscriptTargetChars=transcript_target_chars,
    )


def render_history_page(selected_id=None, message=""):
    records = images_db.get_recent_pictures()
    images = []
    selected = None

    for id, timestamp, _title, img in records:
        item = {
            "ID": id,
            "Timestamp": timestamp,
            "Image": encode_image(img),
        }
        images.append(item)
        if selected_id == id:
            selected = item

    if selected is None and images:
        selected = images[0]

    if selected is None and message == "":
        message = "No images yet."

    return render_template(
        'mobile_history.html',
        Images=images,
        Selected=selected,
        Message=message,
    )


def render_no_images_page():
    return render_image_page(0, message="No images yet.")


def render_transcript_failure_page(
    transcript,
    title,
    style,
    description,
    page_renderer=render_image_page,
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


def redirect_to_last_history_or_empty_state():
    id_last = images_db.get_last_picture_id()
    if id_last is None:
        return render_no_images_page()
    return redirect(url_for("history", ID=id_last))


def build_full_description(title, style, description):
    full_description = title
    if style:
        full_description = full_description + " (" + style + ")"
    if description:
        full_description = full_description + ": " + description
    return full_description


def encode_image(img):
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='JPEG')
    return base64.b64encode(img_bytes.getvalue()).decode('utf-8')


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

    transcript, title, style, description, img, timestamp = record
    return render_manual_page(
        image_id,
        image=encode_image(img),
        full_description=build_full_description(title, style, description),
        transcript=transcript,
        title=title,
        style=style,
        description=description,
        generated_at=timestamp,
    )


@app.route('/')
@app.route('/index.html')
def home():
    return redirect_to_last_history_or_empty_state()


@app.route('/auto')
def auto():
    return render_auto_page()


@app.route('/auto/generate', methods=['POST'])
def auto_generate():
    payload = request.get_json(silent=True) or {}
    transcript = (
        payload.get("transcript")
        or request.form.get("transcript")
        or request.form.get("Transcript")
        or ""
    )
    transcript_value = transcript.strip()

    if transcript_value == "":
        return jsonify({
            "message": "No transcript text was received.",
        }), 400

    try:
        title, style, description = (
            get_image_generator().generate_title(transcript_value)
        )
    except Exception as exc:
        return jsonify({
            "message": "Could not generate a title from the transcript: "
                       + str(exc),
        }), 500

    title_value = title.strip()
    style_value = style.strip()
    description_value = description.strip()
    if title_value == "":
        return jsonify({
            "message": "Could not generate a title from the transcript.",
        }), 500

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
        return jsonify({
            "message": "Image generation failed: " + str(exc),
        }), 500

    picture = build_auto_picture_payload(new_id)
    if picture is None:
        return jsonify({
            "message": "Generated image was saved, but could not be loaded.",
        }), 500

    return jsonify({
        "message": "Picture generated.",
        "picture": picture,
    })


@app.route('/manual')
def manual():
    return render_manual_page()


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.ico',mimetype='image/vnd.microsoft.icon')


@app.route('/history')
def history_index():
    selected_id = request.args.get("ID", type=int)
    return render_history_page(selected_id)


@app.route('/history/<int:ID>', methods=['GET', 'POST'])
def history (ID):
    # Use low case variable locally
    id = ID

    if request.method == "POST":
        # Navigation buttons
        nav = request.form.get("nav")
        nav_previous = nav == "Previous"
        nav_next = nav == "Next"
        nav_last = nav == "Last"
        if nav_last:
            return redirect_to_last_history_or_empty_state()
        if nav_previous:
            if id > 1:
                id = id - 1
            return redirect(url_for("history", ID = id))
        elif nav_next:
            id_last = images_db.get_last_picture_id()
            if id_last is None:
                return render_no_images_page()
            if id < id_last:
                id = id + 1
            return redirect(url_for("history", ID = id))

    record = images_db.get_picture(id)
    if record is None:
        return render_image_page(id, message="No image found for ID " + str(id) + ".")

    transcript_last, title_last, style_last, description_last, img_last = record

    full_description = build_full_description(title_last, style_last, description_last)
    print ("Image prompt: " + full_description)

    return render_image_page(
        id,
        image=encode_image(img_last),
        full_description=full_description,
        transcript=transcript_last,
        title=title_last,
        style=style_last,
        description=description_last,
    )


@app.route('/txt2img', methods=['POST'])
def txt2img():
    return handle_txt2img(render_image_page)


@app.route('/manual/txt2img', methods=['POST'])
def manual_txt2img():
    return handle_txt2img(
        render_manual_page,
        success_renderer=render_manual_success_page,
    )


def handle_txt2img(failure_renderer, success_renderer=None):
    transcript = request.form.get('Transcript', '')
    title = request.form.get('Title', '')
    style = request.form.get('Style', '')
    description = request.form.get('Description', '')

    transcript_value = transcript.strip()
    title_value = title.strip()
    style_value = style.strip()
    description_value = description.strip()

    if transcript_value != "":
        print("Transcript provided: " + transcript_value)
        try:
            generated_title, generated_style, generated_description = (
                get_image_generator().generate_title(transcript_value)
            )
        except Exception as exc:
            print("Title generation failed: " + str(exc))
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
        return failure_renderer(
            0,
            message="Enter a title or transcript before generating an image.",
            transcript=transcript,
            title=title,
            style=style,
            description=description,
        )

    full_description = build_full_description(
        title_value,
        style_value,
        description_value,
    )
    print("Image prompt: " + full_description)

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
        print("Image generation failed: " + str(exc))
        return failure_renderer(
            0,
            message="Image generation failed. Your form values were kept.",
            transcript=transcript,
            title=title,
            style=style,
            description=description,
        )

    if success_renderer is not None:
        return success_renderer(new_id)

    return redirect(url_for("history", ID = new_id))


if __name__ == '__main__':
    app.run(debug = True)
