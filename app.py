import os
import io
import base64

from flask import Flask, render_template, request
from PIL import Image

from config import config
from image_gen import image_gen
from database import database


app = Flask(__name__)

# Misc variables
#temp_file = os.path.join("static", "tmp.png")
image_generator = image_gen(config)
images_db = database(config)


@app.route('/')
@app.route('/index')
def home():
    id = request.args.get("ID")
    if id != None and id.isnumeric():
        transcript_last, title_last, style_last, description_last, img_last = images_db.get_picture(id)
    else:
        # Show the last picture by default
        transcript_last, title_last, style_last, description_last, img_last = images_db.get_last_picture()
    
    # Encode image into html
    img_bytes = io.BytesIO()
    img_last.save(img_bytes, format='JPEG')
    img_encoded = base64.b64encode(img_bytes.getvalue())
    
    # Current image description
    full_description = title_last + " (" + style_last + "): " + description_last
    print ("Image prompt: " + full_description)

    return render_template('index.html', Image = img_encoded.decode('utf-8'), FullDescription = full_description)


@app.route('/txt2img', methods=['POST'])
def txt2img():
    transcript = request.form['Transcript']
    title = request.form['Title']
    style = request.form['Style']
    description = request.form['Description']

    if transcript != "":
        print ("Transcriopt provided: " + transcript)
        title, style, description = image_generator.generate_title(transcript)
    
    # We can now generate an image
    full_description = title + " (" + style + "): " + description
    print ("Image prompt: " + full_description)
    img = image_generator.generate_image(title, style, description)

    # Save to database
    images_db.add_picture(transcript, title, style, description, img)
    
    # Encode image into html
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='JPEG')
    img_encoded = base64.b64encode(img_bytes.getvalue())

    return render_template('index.html', Image = img_encoded.decode('utf-8'), FullDescription = full_description)
    

if __name__ == '__main__':
    app.run(debug = True)
