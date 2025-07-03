from flask import Blueprint, request, jsonify
from firebase_admin import firestore
from controllers.auth_decorators import auth_required, admin_required
from services.auth_service import AuthService
from services.posts_service import PostService
from config import db
from services.face_recognition_service import FaceRecognitionService
import requests
from schemas.post_schema import MissingPostSchema, FoundPostSchema, UpdatePostSchema
from pydantic import ValidationError
from datetime import datetime

face_service = FaceRecognitionService()
posts_bp = Blueprint("posts", __name__)

# ───────── create missing-person post ─────────────────────────
@posts_bp.route("/posts/missing", methods=["POST"])
@auth_required
def create_missing_post():
    if "image_file" not in request.files:
        return jsonify(error="image_file is required"), 400
    try:
        form = MissingPostSchema(**request.form.to_dict())
    except ValidationError as e:
        return jsonify(e.errors()), 400

    profile = AuthService.get_user_profile(request.uid)
    author = f"{profile.first_name} {profile.last_name}".strip()

    try:
        post_id, url = PostService.create_missing_post(
            request.uid,
            author,
            {
                "missing_name": form.missing_name,
                "missing_age": form.missing_age,
                "last_seen": form.last_seen,
                "notes": form.notes,
                "gender": form.gender,   # ← added
            },
            request.files["image_file"],
        )
        return jsonify(
            message="Missing-person post created",
            post_id=post_id,
            image_url=url
        ), 201
    except ValueError as ve:
        return jsonify(error=str(ve)), 400
    except Exception as e:
        return jsonify(error=str(e)), 500

# ───────── create found-person post ───────────────────────────
@posts_bp.route("/posts/found", methods=["POST"])
@auth_required
def create_found_post():
    if "image_file" not in request.files:
        return jsonify(error="image_file is required"), 400
    try:
        form = FoundPostSchema(**request.form.to_dict())
    except ValidationError as e:
        return jsonify(e.errors()), 400

    profile = AuthService.get_user_profile(request.uid)
    author = f"{profile.first_name} {profile.last_name}".strip()

    try:
        post_id, url = PostService.create_found_post(
            request.uid,
            author,
            {
                "found_name": form.found_name,
                "estimated_age": form.estimated_age,
                "found_location": form.found_location,
                "notes": form.notes,
                "gender": form.gender,   # ← added
            },
            request.files["image_file"],
        )
        return jsonify(
            message="Found-person post created",
            post_id=post_id,
            image_url=url
        ), 201
    except ValueError as ve:
        return jsonify(error=str(ve)), 400
    except Exception as e:
        return jsonify(error=str(e)), 500

# ───────── update post ─────────────────────────────────────
@posts_bp.route("/posts/<post_id>", methods=["PATCH"])
@auth_required
def update_post(post_id):
    try:
        update_fields = UpdatePostSchema(**request.form.to_dict()).dict(exclude_unset=True)
    except ValidationError as e:
        return jsonify(e.errors()), 400

    # handle new image if provided
    image_url = None
    if "image_file" in request.files:
        doc = db.collection("posts").document(post_id).get()
        post_type = doc.get("post_type", "missing") if doc.exists else "missing"
        try:
            image_url = PostService._upload_image(
                request.files["image_file"], request.uid, post_type
            )
            update_fields["image_url"] = image_url
        except Exception as e:
            return jsonify(error=str(e)), 400

    try:
        PostService.update_post(post_id, request.uid, update_fields)
        response = {"message": "Post updated"}
        if image_url:
            response["image_url"] = image_url
        return jsonify(response), 200
    except ValueError as ve:
        return jsonify(error=str(ve)), 400
    except Exception as e:
        return jsonify(error=str(e)), 500

# ───────── list all posts ────────────────────────────────────
@posts_bp.route("/posts", methods=["GET"])
def get_posts():
    try:
        posts = PostService.get_posts()
        filtered = []
        for post in posts:
            filtered.append({
                "id": post.id,
                "author_name": post.author_name,
                "created_at": post.get_created_at_iso(),
                "image_url": post.image_url,
                "status": post.status,
                "missing_name": post.payload.get("missing_name"),
                "missing_age": post.payload.get("missing_age"),
                "last_seen": post.payload.get("last_seen"),
                "found_name": post.payload.get("found_name"),
                "estimated_age": post.payload.get("estimated_age"),
                "found_location": post.payload.get("found_location"),
                "notes": post.payload.get("notes"),
                "gender": post.payload.get("gender"),  # ← added
            })
        return jsonify(posts=filtered), 200
    except Exception as e:
        return jsonify(error=str(e)), 500

# ───────── get single post ────────────────────────────────────
@posts_bp.route("/posts/<post_id>", methods=["GET"])
def get_post(post_id):
    try:
        post = PostService.get_post(post_id)
        if not post:
            return jsonify(error="Post not found"), 404

        return jsonify(post={
            "id": post.id,
            "author_name": post.author_name,
            "created_at": post.get_created_at_iso(),
            "image_url": post.image_url,
            "status": post.status,
            "missing_name": post.payload.get("missing_name"),
            "missing_age": post.payload.get("missing_age"),
            "last_seen": post.payload.get("last_seen"),
            "found_name": post.payload.get("found_name"),
            "estimated_age": post.payload.get("estimated_age"),
            "found_location": post.payload.get("found_location"),
            "notes": post.payload.get("notes"),
            "gender": post.payload.get("gender"),  # ← added
        }), 200

    except Exception as e:
        return jsonify(error=str(e)), 500

# (other endpoints unchanged)
