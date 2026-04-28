import os
import io
import base64

from flask import Flask, render_template, request, redirect, url_for, send_from_directory

from config import config
from database import database


app = Flask(__name__)

# Misc variables
#temp_file = os.path.join("static", "tmp.png")
image_generator = None
images_db = database(config)


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


def render_no_images_page():
    return render_image_page(0, message="No images yet.")


def render_transcript_failure_page(transcript, title, style, description):
    return render_image_page(
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


@app.route('/')
@app.route('/index.html')
def home():
    return redirect_to_last_history_or_empty_state()


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.ico',mimetype='image/vnd.microsoft.icon')


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

    img_bytes = io.BytesIO()
    img_last.save(img_bytes, format='JPEG')
    img_encoded = base64.b64encode(img_bytes.getvalue())

    full_description = build_full_description(title_last, style_last, description_last)
    print ("Image prompt: " + full_description)

    return render_image_page(
        id,
        image=img_encoded.decode('utf-8'),
        full_description=full_description,
        transcript=transcript_last,
        title=title_last,
        style=style_last,
        description=description_last,
    )


@app.route('/txt2img', methods=['POST'])
def txt2img():
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
            )

        if generated_title.strip() == "":
            return render_transcript_failure_page(
                transcript,
                title,
                style,
                description,
            )

        title = generated_title
        style = generated_style
        description = generated_description
        title_value = title.strip()
        style_value = style.strip()
        description_value = description.strip()

    if title_value == "":
        return render_image_page(
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
        return render_image_page(
            0,
            message="Image generation failed. Your form values were kept.",
            transcript=transcript,
            title=title,
            style=style,
            description=description,
        )

    return redirect(url_for("history", ID = new_id))


if __name__ == '__main__':
    app.run(debug = True)
