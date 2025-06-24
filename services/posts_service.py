# services/posts_service.py
import uuid, io
from urllib.parse import urlparse, unquote

import numpy as np
from firebase_admin import storage, firestore
from google.cloud.exceptions import NotFound
from config import db
from services.image_service import preprocess


class PostService:
    # ───────── private helpers ──────────────────────────
    @staticmethod
    def _gcs_delete(download_url: str) -> None:
        """Delete a blob given any Firebase or public download URL."""
        bucket = storage.bucket()
        blob_name = None

        p = urlparse(download_url)
        if "/o/" in p.path:                             # v0 / v1 signed URL
            blob_name = unquote(p.path.split("/o/")[1])
        else:                                           # public URL
            path = p.path.lstrip("/")
            if path.startswith(bucket.name + "/"):
                blob_name = path[len(bucket.name) + 1:]

        if blob_name:
            try:
                bucket.blob(blob_name).delete()
            except NotFound:
                pass  # already gone

    @staticmethod
    def _upload_image(file_storage, uid: str, post_type: str) -> str:
        """
        Uploads an image and makes it public.

        • missing posts  →  gs://bucket/missing_posts/<uid>/<uuid>.jpg
        • found   posts  →  gs://bucket/found_posts/<uuid>.jpg
        """
        raw = file_storage.read()
        clean_bytes, _ = preprocess(raw)

        if post_type == "missing":
            blob_path = f"missing_posts/{uid}/{uuid.uuid4()}.jpg"
        else:  # "found"
            blob_path = f"found_posts/{uuid.uuid4()}.jpg"

        blob = storage.bucket().blob(blob_path)
        blob.upload_from_file(io.BytesIO(clean_bytes),
                              content_type="image/jpeg")
        blob.make_public()
        return blob.public_url


    @classmethod
    def _create_post_base(
        cls,
        uid: str,
        author_name: str,
        payload: dict,
        file_storage,
        post_type: str,
    ):
        image_url = cls._upload_image(file_storage, uid, post_type)
        doc = {
            "uid": uid,
            "author_name": author_name,
            "post_type": post_type,                     # ← NEW FIELD
            "image_url": image_url,
            "created_at": firestore.SERVER_TIMESTAMP,
            "status": "active",
            **payload,
        }
        ref = db.collection("posts").document()
        ref.set(doc)
        return ref.id, image_url

    # ───────── public creators ─────────────────────────
    @classmethod
    def create_missing_post(cls, uid, author, payload, file_storage):
        return cls._create_post_base(uid, author, payload, file_storage, "missing")

    @classmethod
    def create_found_post(cls, uid, author, payload, file_storage):
        return cls._create_post_base(uid, author, payload, file_storage, "found")

    # ───────── updates & deletes ───────────────────────
    @classmethod
    def update_post(cls, post_id: str, uid: str, update_fields: dict):
        ref = db.collection("posts").document(post_id)
        doc = ref.get()
        if not doc.exists or doc.get("uid") != uid:
            raise ValueError("Post not found or unauthorized")
        ref.update(update_fields)

    @classmethod
    def delete_post_for_user(cls, post_id: str, uid: str):
        cls._delete_post_common(post_id, uid, is_admin=False)

    @classmethod
    def delete_post_for_admin(cls, post_id: str):
        # admin: we first read owner uid to satisfy signature
        doc = db.collection("posts").document(post_id).get()
        if not doc.exists:
            raise ValueError("Post not found")
        owner_uid = doc.get("uid", "")
        cls._delete_post_common(post_id, owner_uid, is_admin=True)

    @classmethod
    def _delete_post_common(cls, post_id: str, owner_uid: str, is_admin: bool):
        doc_ref = db.collection("posts").document(post_id)
        doc = doc_ref.get()
        if not doc.exists:
            raise ValueError("Post not found")

        if not is_admin and doc.get("uid") != owner_uid:
            raise ValueError("Forbidden")

        if img_url := doc.get("image_url"):
            cls._gcs_delete(img_url)

        doc_ref.delete()
        db.collection("post_reports").document(post_id).delete()

    # ───────── retrieval ──────────────────────────────
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
