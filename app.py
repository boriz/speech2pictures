import os
import io
import base64

from flask import Flask, render_template, request, redirect, url_for
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
@app.route('/index.html')
def home():
    # Just show the latest picture by default
    id_last = images_db.get_last_picture_id()
    return redirect(url_for("history", ID = id_last))


@app.route('/history/<int:ID>', methods=['GET', 'POST'])
def history (ID):
    # Use low case variable locally
    id = ID
    
    if request.method == "POST":
        # Navigation buttons
        nav_previous = request.form["nav"] != None and request.form["nav"] == "Previous"
        nav_next = request.form["nav"] != None and request.form["nav"]== "Next"
        nav_last = request.form["nav"] != None and request.form["nav"]== "Last"
        if nav_last:
            # Last button
            id_last = images_db.get_last_picture_id()
            return redirect(url_for("history", ID = id_last))
        if nav_previous:
            # Prev button
            if id > 1:
                id = id - 1
            return redirect(url_for("history", ID = id))
        elif nav_next:
            # Next button
            id_last = images_db.get_last_picture_id()
            if id < id_last:
                id = id + 1
            return redirect(url_for("history", ID = id))
        
    # We shold have a valid id at this point
    transcript_last, title_last, style_last, description_last, img_last = images_db.get_picture(id)
    
    # Encode image into html
    img_bytes = io.BytesIO()
    img_last.save(img_bytes, format='JPEG')
    img_encoded = base64.b64encode(img_bytes.getvalue())
    
    # Current image description
    full_description = title_last + " (" + style_last + "): " + description_last
    print ("Image prompt: " + full_description)

    return render_template('index.html', ID = id, Image = img_encoded.decode('utf-8'), FullDescription = full_description)


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
    new_id = images_db.add_picture(transcript, title, style, description, img)
    
    return redirect(url_for("history", ID = new_id))
    

if __name__ == '__main__':
    app.run(debug = True)
