import uuid, imghdr, io
from datetime import datetime
from services.image_service import preprocess
from firebase_admin import storage, firestore
from config import db             
ALLOWED_TYPES = {"jpeg", "png"}

class PostService:
    @staticmethod
    def _upload_image(file_storage, uid: str) -> str:
        """Preprocesses and uploads an image, returning the public URL."""
        raw = file_storage.read()

        try:
            clean_bytes, img_type = preprocess(raw)
        except ValueError as ve:
            # user-facing validation failure
            raise
        except Exception:
            raise ValueError("Image processing failed")

        ext  = "jpg"  # preprocess always returns jpeg now
        name = f"posts/{uid}/{uuid.uuid4()}.{ext}"

        blob = storage.bucket().blob(name)
        blob.upload_from_file(io.BytesIO(clean_bytes),
                              content_type="image/jpeg")
        blob.make_public()
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

    @classmethod
    def update_post(cls, post_id: str, uid: str, update_fields: dict):
        ref = db.collection("posts").document(post_id)
        doc = ref.get()
        if not doc.exists or doc.to_dict().get("uid") != uid:
            raise ValueError("Post not found or unauthorized")
        ref.update(update_fields)

    @classmethod
    def delete_post(cls, post_id: str, uid: str):
        ref = db.collection("posts").document(post_id)
        doc = ref.get()
        if not doc.exists or doc.to_dict().get("uid") != uid:
            raise ValueError("Post not found or unauthorized")
        ref.delete()

    @classmethod
    def get_posts(cls):
        posts = db.collection("posts").order_by("created_at", direction=firestore.Query.DESCENDING).stream()
        return [{**doc.to_dict(), "id": doc.id} for doc in posts]

    @classmethod
    def get_post(cls, post_id: str):
        ref = db.collection("posts").document(post_id)
        doc = ref.get()
        if not doc.exists:
            return None
        return {**doc.to_dict(), "id": doc.id}
