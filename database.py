import sqlite3
import os
import io
import config

from PIL import Image
from config import config


class database:
    def __init__(self, config):
        db_is_new = not os.path.exists(config.db_file_name)
        conn = sqlite3.connect(config.db_file_name)
        if db_is_new:
            print ("Creating database: " + config.db_file_name)
            sql = "create table if not exists tblImages( \
            ID INTEGER PRIMARY KEY AUTOINCREMENT, \
            Timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, \
            Transcript TEXT, \
            Title TEXT, \
            Style TEXT, \
            Description TEXT, \
            Image BLOB); "
            conn.execute(sql)
        else:
            print ("Database already exists")


    def add_picture(self, transcript, title, style, description, img):
        conn = sqlite3.connect(config.db_file_name)
        cursor = conn.cursor()
        sql = "INSERT INTO tblImages (Transcript, Title, Style, Description, Image) VALUES(?, ?, ?, ?, ?);"
        
        with io.BytesIO() as img_bytes:
            img.save(img_bytes, format='JPEG')
            img_bytes = img_bytes.getvalue()
        cursor.execute(sql,[transcript, title, style, description, sqlite3.Binary(img_bytes)]) 
        conn.commit()
        return cursor.lastrowid


    def get_picture(self, id):
        conn = sqlite3.connect(config.db_file_name)
        cursor = conn.cursor()
        sql = "SELECT Transcript, Title, Style, Description, Image FROM tblImages WHERE ID = :id;"
        param = {'id': id}
        cursor.execute(sql, param)
        transcript, title, style, description, img_bytes = cursor.fetchone()
        img = Image.open(io.BytesIO(img_bytes))
        return transcript, title, style, description, img


    def get_last_picture(self):
        conn = sqlite3.connect(config.db_file_name)
        cursor =conn.cursor()
        sql = "SELECT Transcript, Title, Style, Description, Image FROM tblImages ORDER BY ID DESC LIMIT 1;"
        cursor.execute(sql)
        transcript, title, style, description, img_bytes = cursor.fetchone()
        img = Image.open(io.BytesIO(img_bytes))
        return transcript, title, style, description, img


if __name__ == "__main__":
    # Basic test code
    db_test = database(config)
    img = Image.open("tmp.png")
    id = db_test.add_picture("test transcript", "test title", "test style", "test description", img)
    print("Saved to DB, id: " + str(id))

    transcript_last, title_last, style_last, description_last, img_last = db_test.get_last_picture()
    print("Last image title: " + title_last + ". (" + style_last + "): " + description_last)
    img_last.save("db_test.jpg")

    transcript, title, style, description, img = db_test.get_picture(1)
    print("Get picture with ID = 1: " + title)
    img.save("db_test_1.jpg")
