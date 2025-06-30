import uuid, io
from urllib.parse import urlparse, unquote

import numpy as np
from firebase_admin import storage, firestore
from google.cloud.exceptions import NotFound
from config import db
from services.image_service import preprocess
from repositories.post_repository import PostRepository
from factories.image_uploader_factory import ImageUploaderFactory
from models.post_model import Post



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
        uploader = ImageUploaderFactory.get_uploader(post_type)
        return uploader.upload(file_storage, uid)


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
        post_id = str(uuid.uuid4())
        post = Post(
            id=post_id,
            uid=uid,
            author_name=author_name,
            post_type=post_type,
            image_url=image_url,
            created_at=firestore.SERVER_TIMESTAMP,
            status="active",
            payload=payload
        )
        PostRepository.create_post(post.id, post.to_dict())
        return post.id, image_url

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
        doc = PostRepository.get_post_by_id(post_id)
        if not doc.exists or doc.get("uid") != uid:
            raise ValueError("Post not found or unauthorized")
        PostRepository.update_post(post_id, update_fields)

    @classmethod
    def delete_post_for_user(cls, post_id: str, uid: str):
        cls._delete_post_common(post_id, uid, is_admin=False)

    @classmethod
    def delete_post_for_admin(cls, post_id: str):
    # admin: we first read owner uid to satisfy signature
        doc = PostRepository.get_post_by_id(post_id)
        if not doc.exists:
            raise ValueError("Post not found")

        # convert the DocumentSnapshot to a dict before reading fields
        data = doc.to_dict() or {}
        owner_uid = data.get("uid", "")

        cls._delete_post_common(post_id, owner_uid, is_admin=True)


    @classmethod
    def _delete_post_common(cls, post_id: str, owner_uid: str, is_admin: bool):
        doc = PostRepository.get_post_by_id(post_id)
        if not doc.exists:
            raise ValueError("Post not found")

        if not is_admin and doc.get("uid") != owner_uid:
            raise ValueError("Forbidden")

        if img_url := doc.get("image_url"):
            cls._gcs_delete(img_url)

        PostRepository.delete_post(post_id)
        PostRepository.delete_post_report(post_id)

    # ───────── retrieval ──────────────────────────────
    @classmethod
    def get_posts(cls):
        posts = PostRepository.get_all_posts()
        return [Post.from_dict(d.id, d.to_dict()) for d in posts]

    @classmethod
    def get_post(cls, post_id: str):
        doc = PostRepository.get_post_by_id(post_id)
        return None if not doc.exists else Post.from_dict(doc.id, doc.to_dict())

    @staticmethod
    def download_image(url: str) -> bytes:
        """Download image from Firebase Storage URL"""
        from urllib.parse import urlparse, unquote
        import requests

        # Parse URL to extract blob path
        parsed = urlparse(url)
        if "firebasestorage.googleapis.com" in parsed.netloc:
            # Extract blob path from Firebase URL
            path_segments = parsed.path.split("/o/")
            if len(path_segments) > 1:
                blob_path = unquote(path_segments[1].split("?")[0])

                # Download from Firebase Storage
                bucket = storage.bucket()
                blob = bucket.blob(blob_path)
                return blob.download_as_bytes()

        # Fallback to regular download
        response = requests.get(url)
        response.raise_for_status()
        return response.content

