from flask import Blueprint, request, jsonify, current_app
from firebase_admin import firestore
from controllers.auth_decorators import auth_required, admin_required
from services.auth_service import AuthService
from services.posts_service import PostService
from services.face_recognition_service import FaceRecognitionService
from config import db
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
                "missing_age":  form.missing_age,
                "last_seen":    form.last_seen,
                "notes":        form.notes,
                "gender":       form.gender,   # ← gender field
            },
            request.files["image_file"],
        )
        return jsonify(message="Missing-person post created",
                       post_id=post_id,
                       image_url=url), 201
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
                "found_name":    form.found_name,
                "estimated_age": form.estimated_age,
                "found_location": form.found_location,
                "notes":         form.notes,
                "gender":        form.gender,   # ← gender field
            },
            request.files["image_file"],
        )
        return jsonify(message="Found-person post created",
                       post_id=post_id,
                       image_url=url), 201
    except ValueError as ve:
        return jsonify(error=str(ve)), 400
    except Exception as e:
        return jsonify(error=str(e)), 500

# ───────── update post ─────────────────────────────────────
@posts_bp.route("/posts/<post_id>", methods=["PATCH"])
@auth_required
def update_post(post_id):
    # 1) collect & validate only the fields you care about
    try:
        update_fields = UpdatePostSchema(**request.form.to_dict()) \
                            .dict(exclude_unset=True)
    except ValidationError as e:
        return jsonify(e.errors()), 400

    # debug — log exactly what we’re about to write
    current_app.logger.debug(f"PATCH /posts/{post_id} → {update_fields}")

    # 2) handle a new image upload if present
    if "image_file" in request.files:
        doc = db.collection("posts").document(post_id).get()
        post_type = doc.get("post_type", "missing") if doc.exists else "missing"
        try:
            new_url = PostService._upload_image(
                request.files["image_file"], request.uid, post_type
            )
            update_fields["image_url"] = new_url
        except Exception as e:
            return jsonify(error=str(e)), 400

    # 3) actually write it
    try:
        PostService.update_post(post_id, request.uid, update_fields)
    except ValueError as ve:
        return jsonify(error=str(ve)), 400
    except Exception as e:
        return jsonify(error=str(e)), 500

    # 4) fetch & return the *new* record so you see the change immediately
    updated = PostService.get_post(post_id)
    # build a small JSON-friendly payload
    result = {
        "id":             updated.id,
        "image_url":      updated.image_url,
        "missing_name":   updated.payload.get("missing_name"),
        "missing_age":    updated.payload.get("missing_age"),
        "last_seen":      updated.payload.get("last_seen"),
        "found_name":     updated.payload.get("found_name"),
        "estimated_age":  updated.payload.get("estimated_age"),
        "found_location": updated.payload.get("found_location"),
        "notes":          updated.payload.get("notes"),
        "gender":         updated.payload.get("gender"),
    }
    return jsonify(message="Post updated", post=result), 200

# ───────── delete post (user) ───────────────────────────────
@posts_bp.route("/posts/<post_id>", methods=["DELETE"])
@auth_required
def delete_post(post_id):
    try:
        PostService.delete_post_for_user(post_id, request.uid)
        return jsonify(message="Post deleted"), 200
    except ValueError as ve:
        return jsonify(error=str(ve)), 400
    except Exception as e:
        return jsonify(error=str(e)), 500

# ───────── delete post (admin) ──────────────────────────────
@posts_bp.route("/admin/posts/<post_id>", methods=["DELETE"])
@admin_required
def admin_delete_post(post_id):
    try:
        PostService.delete_post_for_admin(post_id)
        return jsonify(message="Post deleted by admin"), 200
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
                "id":             post.id,
                "author_name":    post.author_name,
                "created_at":     post.get_created_at_iso(),
                "image_url":      post.image_url,
                "status":         post.status,
                "missing_name":   post.payload.get("missing_name"),
                "missing_age":    post.payload.get("missing_age"),
                "last_seen":      post.payload.get("last_seen"),
                "found_name":     post.payload.get("found_name"),
                "estimated_age":  post.payload.get("estimated_age"),
                "found_location": post.payload.get("found_location"),
                "notes":          post.payload.get("notes"),
                "gender":         post.payload.get("gender"),  # ← gender
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
            "id":             post.id,
            "author_name":    post.author_name,
            "created_at":     post.get_created_at_iso(),
            "image_url":      post.image_url,
            "status":         post.status,
            "missing_name":   post.payload.get("missing_name"),
            "missing_age":    post.payload.get("missing_age"),
            "last_seen":      post.payload.get("last_seen"),
            "found_name":     post.payload.get("found_name"),
            "estimated_age":  post.payload.get("estimated_age"),
            "found_location": post.payload.get("found_location"),
            "notes":          post.payload.get("notes"),
            "gender":         post.payload.get("gender"),  # ← gender
        }), 200

    except Exception as e:
        return jsonify(error=str(e)), 500

@posts_bp.route("/posts/<post_id>/report", methods=["POST"])
@auth_required
def report_post(post_id):
    reason = (request.get_json() or {}).get("reason", "")
    # now add a new report document (auto-ID) so multiple reports accumulate
    db.collection("post_reports").add({
        "post_id":    post_id,
        "reporter":   request.uid,
        "reason":     reason[:200],
        "created_at": firestore.SERVER_TIMESTAMP,
    })
    return jsonify(message="report submitted"), 201

# ───────── search for missing ────────────────────────────────
@posts_bp.route("/search", methods=["POST"])
@auth_required
def search_for_missing():
    if "image_file" not in request.files:
        return jsonify(error="image_file is required"), 400

    search_image_bytes = request.files["image_file"].read()
    try:
        all_posts = PostService.get_posts()
        matches = []
        for post in all_posts:
            # only compare to 'found' posts
            if post.post_type != "found":
                continue
            img_url = post.image_url
            if not img_url:
                continue
            try:
                resp = requests.get(img_url, timeout=5)
                resp.raise_for_status()
                post_image_bytes = resp.content
            except Exception:
                continue

            distance = face_service.compare_faces(search_image_bytes, post_image_bytes)
            if distance < FaceRecognitionService.THRESHOLD:
                matches.append({
                    "post_id":      post.id,
                    "distance":     float(distance),
                    "post_details": post.to_dict(),
                })

        # return closest match or message if none
        if not matches:
            return jsonify(message="No match found"), 200

        closest = min(matches, key=lambda x: x["distance"])
        # log for admin stats
        db.collection("match_stats").add({
            "timestamp": datetime.utcnow(),
            "success":   True
        })
        return jsonify(closest_match=closest), 200

    except Exception as e:
        return jsonify(error=str(e)), 500
