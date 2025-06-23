import uuid, io
from urllib.parse import urlparse, unquote

from services.image_service import preprocess
from firebase_admin import storage, firestore
from config import db


class PostService:
    # ────────────────── helpers ──────────────────────────
    @staticmethod
    def _delete_blob_from_url(download_url: str) -> None:
        parsed = urlparse(download_url)
        bucket = storage.bucket()

        blob_name = None

        if "/o/" in parsed.path:                          # both v0 and v1 API forms
            blob_part = parsed.path.split("/o/")[1]       # posts%2Fpic.jpg
            blob_name = unquote(blob_part)
        else:
            # public URL → /<bucket>/posts/pic.jpg
            parts = parsed.path.lstrip("/").split("/", 1)  # ["<bucket>", "posts/pic.jpg"]
            if len(parts) == 2 and parts[0] == bucket.name:
                blob_name = parts[1]

        if not blob_name:
            # Unrecognised format; nothing to delete
            return

        try:
            bucket.blob(blob_name).delete()
        except Exception:
            # object already gone – ignore
            pass
    # ────────────────── image upload ─────────────────────
    @staticmethod
    def _upload_image(file_storage, uid: str) -> str:
        raw = file_storage.read()
        clean_bytes, _ = preprocess(raw)          # returns jpeg
        name = f"posts/{uid}/{uuid.uuid4()}.jpg"

        blob = storage.bucket().blob(name)
        blob.upload_from_file(io.BytesIO(clean_bytes),
                              content_type="image/jpeg")
        blob.make_public()
        return blob.public_url

    # ────────────────── CRUD methods ─────────────────────
    @classmethod
    def create_post(cls, uid: str, author_name: str, payload: dict, file_storage):
        image_url = cls._upload_image(file_storage, uid)
        doc = {
            "uid": uid,
            "author_name": author_name,
            **payload,
            "image_url": image_url,
            "created_at": firestore.SERVER_TIMESTAMP,
            "status": "active",
        }
        ref = db.collection("posts").document()
        ref.set(doc)
        return ref.id, image_url

    @classmethod
    def update_post(cls, post_id: str, uid: str, update_fields: dict):
        ref = db.collection("posts").document(post_id)
        doc = ref.get()
        if not doc.exists or doc.get("uid") != uid:
            raise ValueError("Post not found or unauthorized")
        ref.update(update_fields)

    @classmethod
    def delete_post(cls, post_id: str, owner_uid: str, *, as_admin=False):
        doc_ref = db.collection("posts").document(post_id)
        doc = doc_ref.get()
        if not doc.exists:
            raise ValueError("Post not found")

        # Use to_dict() to access fields
        if not as_admin and doc.to_dict().get("uid") != owner_uid:
            raise ValueError("Forbidden")

        # remove the image file, if any
        image_url = doc.to_dict().get("image_url")
        if image_url:
            cls._delete_blob_from_url(image_url)

        # delete the Firestore post doc
        doc_ref.delete()
        # also drop any report entry
        db.collection("post_reports").document(post_id).delete()

    @classmethod
    def delete_post_for_user(cls, post_id: str, uid: str):
        cls.delete_post(post_id, uid, as_admin=False)

    @classmethod
    def delete_post_for_admin(cls, post_id: str):
        # For admin deletion, we don't need to check owner_uid, so we can pass None or an empty string
        cls.delete_post(post_id, owner_uid="", as_admin=True)

    # ────────────────── retrieval ────────────────────────
    @classmethod
    def get_posts(cls):
        posts = (
            db.collection("posts")
              .order_by("created_at", direction=firestore.Query.DESCENDING)
              .stream()
        )
        return [{**d.to_dict(), "id": d.id} for d in posts]

    @classmethod
    def get_post(cls, post_id: str):
        doc = db.collection("posts").document(post_id).get()
        return None if not doc.exists else {**doc.to_dict(), "id": doc.id}


