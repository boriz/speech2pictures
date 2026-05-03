import sqlite3
import os
import io
import config

from PIL import Image
from config import config


class database:
    def __init__(self, config):
        self.db_file_name = config.db_file_name
        db_is_new = not os.path.exists(config.db_file_name)
        sql = "create table if not exists tblImages( \
        ID INTEGER PRIMARY KEY AUTOINCREMENT, \
        Timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, \
        Transcript TEXT, \
        Title TEXT, \
        Style TEXT, \
        Description TEXT, \
        Image BLOB); "

        with sqlite3.connect(self.db_file_name) as conn:
            if db_is_new:
                print ("Creating database: " + self.db_file_name)
            else:
                print ("Database already exists")
            conn.execute(sql)


    def add_picture(self, transcript, title, style, description, img):
        with sqlite3.connect(self.db_file_name) as conn:
            cursor = conn.cursor()
            sql = "INSERT INTO tblImages (Transcript, Title, Style, Description, Image) VALUES(?, ?, ?, ?, ?);"
            with io.BytesIO() as img_bytes:
                img.save(img_bytes, format='JPEG')
                img_bytes = img_bytes.getvalue()
            cursor.execute(sql, [transcript, title, style, description, sqlite3.Binary(img_bytes)])
            conn.commit()
            return cursor.lastrowid


    def get_picture(self, id):
        with sqlite3.connect(self.db_file_name) as conn:
            cursor = conn.cursor()
            sql = "SELECT Transcript, Title, Style, Description, Image FROM tblImages WHERE ID = :id;"
            param = {'id': id}
            cursor.execute(sql, param)
            row = cursor.fetchone()

        if row is None:
            return None

        transcript, title, style, description, img_bytes = row
        img = Image.open(io.BytesIO(img_bytes))
        return transcript, title, style, description, img


    def get_picture_with_timestamp(self, id):
        with sqlite3.connect(self.db_file_name) as conn:
            cursor = conn.cursor()
            sql = "SELECT Transcript, Title, Style, Description, Image, Timestamp FROM tblImages WHERE ID = :id;"
            param = {'id': id}
            cursor.execute(sql, param)
            row = cursor.fetchone()

        if row is None:
            return None

        transcript, title, style, description, img_bytes, timestamp = row
        img = Image.open(io.BytesIO(img_bytes))
        return transcript, title, style, description, img, timestamp


    def get_recent_pictures(self, limit=20):
        with sqlite3.connect(self.db_file_name) as conn:
            cursor = conn.cursor()
            sql = "SELECT ID, Timestamp, Title, Image FROM tblImages ORDER BY ID DESC LIMIT :limit;"
            cursor.execute(sql, {"limit": limit})
            rows = cursor.fetchall()

        pictures = []
        for id, timestamp, title, img_bytes in rows:
            img = Image.open(io.BytesIO(img_bytes))
            pictures.append((id, timestamp, title, img))
        return pictures


    def get_last_picture_id(self):
        with sqlite3.connect(self.db_file_name) as conn:
            cursor = conn.cursor()
            sql = "SELECT ID FROM tblImages ORDER BY ID DESC LIMIT 1;"
            cursor.execute(sql)
            row = cursor.fetchone()

        if row is None:
            return None

        return row[0]


if __name__ == "__main__":
    # Basic test code
    db_test = database(config)
    img = Image.open("tmp.png")
    id = db_test.add_picture("test transcript", "test title", "test style", "test description", img)
    print("Saved to DB, id: " + str(id))

    id_last = db_test.get_last_picture_id()
    print("Last image: " + str(id_last))

    picture = db_test.get_picture(1)
    if picture is not None:
        transcript, title, style, description, img = picture
        print("Get picture with ID = 1: " + title)
        img.save("db_test_1.jpg")
