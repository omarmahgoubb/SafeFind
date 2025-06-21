import uuid, imghdr, io
from datetime import datetime
from firebase_admin import storage, firestore
from config import db             
ALLOWED_TYPES = {"jpeg", "png"}

class PostService:
    @staticmethod
    def _upload_image(file_storage, uid: str) -> str:
        raw = file_storage.read()
        img_type = imghdr.what(None, raw)
        if img_type not in ALLOWED_TYPES:
            raise ValueError("Only JPEG and PNG are allowed")

        ext = "jpg" if img_type == "jpeg" else "png"
        filename = f"posts/{uid}/{uuid.uuid4()}.{ext}"

        bucket = storage.bucket()
        blob = bucket.blob(filename)
        blob.upload_from_file(io.BytesIO(raw), content_type=f"image/{ext}")
        blob.make_public()                    # simple for now
        return blob.public_url

    @classmethod
    def create_post(cls, uid: str, author_name: str, payload: dict, file_storage):
        image_url = cls._upload_image(file_storage, uid)
        doc = {
            "uid": uid,
            "author_name": author_name,
            "image_url": image_url,
            **payload,                       # missing_name, age, etc.
            "created_at": firestore.SERVER_TIMESTAMP,
            "status": "active"
        }
        ref = db.collection("posts").document()
        ref.set(doc)
        return ref.id, image_url
