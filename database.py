import sqlite3
import os
import io
import logging

from PIL import Image
from config import config

HISTORY_RECENT_LIMIT_DEFAULT = 50
LOGGER = logging.getLogger(__name__)


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
                LOGGER.info("database_create file=%s", self.db_file_name)
            else:
                LOGGER.info("database_open file=%s", self.db_file_name)
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


    def _decode_image(self, image_bytes, context):
        try:
            image = Image.open(io.BytesIO(image_bytes))
            image.load()
            return image
        except Exception as exc:
            LOGGER.error(
                "database_image_decode_failed context=%s error=%s",
                context,
                str(exc),
            )
            return None


    def get_picture(self, image_id):
        with sqlite3.connect(self.db_file_name) as conn:
            cursor = conn.cursor()
            sql = "SELECT Transcript, Title, Style, Description, Image FROM tblImages WHERE ID = :id;"
            param = {'id': image_id}
            cursor.execute(sql, param)
            row = cursor.fetchone()

        if row is None:
            return None

        transcript, title, style, description, image_bytes = row
        image = self._decode_image(
            image_bytes,
            "get_picture image_id=" + str(image_id),
        )
        if image is None:
            return None
        return transcript, title, style, description, image


    def get_picture_with_timestamp(self, image_id):
        with sqlite3.connect(self.db_file_name) as conn:
            cursor = conn.cursor()
            sql = "SELECT Transcript, Title, Style, Description, Image, Timestamp FROM tblImages WHERE ID = :id;"
            param = {'id': image_id}
            cursor.execute(sql, param)
            row = cursor.fetchone()

        if row is None:
            return None

        transcript, title, style, description, image_bytes, timestamp = row
        image = self._decode_image(
            image_bytes,
            "get_picture_with_timestamp image_id=" + str(image_id),
        )
        if image is None:
            return None
        return transcript, title, style, description, image, timestamp


    def _resolve_recent_limit(self, limit):
        configured_limit = limit
        if configured_limit is None:
            configured_limit = getattr(
                config,
                "history_recent_limit",
                HISTORY_RECENT_LIMIT_DEFAULT,
            )
        try:
            parsed_limit = int(configured_limit)
        except (TypeError, ValueError):
            return HISTORY_RECENT_LIMIT_DEFAULT

        if parsed_limit <= 0:
            return HISTORY_RECENT_LIMIT_DEFAULT

        return parsed_limit


    def get_recent_pictures(self, limit=None):
        resolved_limit = self._resolve_recent_limit(limit)
        with sqlite3.connect(self.db_file_name) as conn:
            cursor = conn.cursor()
            sql = "SELECT ID, Timestamp, Title, Style, Description, Transcript, Image FROM tblImages ORDER BY ID DESC LIMIT :limit;"
            cursor.execute(sql, {"limit": resolved_limit})
            rows = cursor.fetchall()

        pictures = []
        for image_id, timestamp, title, style, description, transcript, image_bytes in rows:
            image = self._decode_image(
                image_bytes,
                "get_recent_pictures image_id=" + str(image_id),
            )
            if image is None:
                continue
            pictures.append(
                (
                    image_id,
                    timestamp,
                    title,
                    style,
                    description,
                    transcript,
                    image,
                )
            )
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
