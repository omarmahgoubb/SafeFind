# controllers/posts_controller.py
from flask import Blueprint, request, jsonify, g
from firebase_admin import firestore
from controllers.auth_decorators import auth_required, admin_required
from services.auth_service import AuthService
from services.posts_service import PostService
from config import db
from services.face_recognition_service import FaceRecognitionService
import requests

face_service = FaceRecognitionService() 

posts_bp = Blueprint("posts", __name__)

# ───────── create missing-person post ─────────────────────────
@posts_bp.route("/posts/missing", methods=["POST"])
@auth_required
def create_missing_post():
    if "image_file" not in request.files:
        return jsonify(error="image_file is required"), 400
    form = request.form.to_dict()
    for fld in ("missing_name", "missing_age", "last_seen"):
        if not form.get(fld):
            return jsonify(error=f"{fld} is required"), 400

    profile = AuthService.get_user_profile(g.uid)
    author  = f"{profile.get('first_name','')} {profile.get('last_name','')}".strip()

    try:
        post_id, url = PostService.create_missing_post(
            g.uid,
            author,
            {
                "missing_name": form["missing_name"],
                "missing_age":  int(form["missing_age"]),
                "last_seen":    form["last_seen"],
                "notes":        form.get("notes", ""),
            },
            request.files["image_file"],
        )
        return jsonify(message="Missing-person post created",
                       post_id=post_id, image_url=url), 201
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
    form = request.form.to_dict()
    for fld in ("found_name", "estimated_age", "found_location"):
        if not form.get(fld):
            return jsonify(error=f"{fld} is required"), 400

    profile = AuthService.get_user_profile(g.uid)
    author  = f"{profile.get('first_name','')} {profile.get('last_name','')}".strip()

    try:
        post_id, url = PostService.create_found_post(
            g.uid,
            author,
            {
                "found_name":     form["found_name"],
                "estimated_age":  int(form["estimated_age"]),
                "found_location": form["found_location"],
                "notes":          form.get("notes", ""),
            },
            request.files["image_file"],
        )
        return jsonify(message="Found-person post created",
                       post_id=post_id, image_url=url), 201
    except ValueError as ve:
        return jsonify(error=str(ve)), 400
    except Exception as e:
        return jsonify(error=str(e)), 500

@posts_bp.route("/posts/<post_id>", methods=["PATCH"])
@auth_required
def update_post(post_id):
    form = request.form.to_dict()
    update_fields = {}
    for fld in ("missing_name", "missing_age", "last_seen", "notes"):
        if fld in form:
            update_fields[fld] = form[fld]
    if "missing_age" in update_fields:
        try:
            update_fields["missing_age"] = int(update_fields["missing_age"])
        except ValueError:
            return jsonify(error="missing_age must be an integer"), 400

    image_url = None
    if "image_file" in request.files:
        # find the post_type to choose the correct folder
        doc = db.collection("posts").document(post_id).get()
        post_type = doc.get("post_type", "missing") if doc.exists else "missing"

        try:
            image_url = PostService._upload_image(
                request.files["image_file"], g.uid, post_type
            )
            update_fields["image_url"] = image_url
        except Exception as e:
            return jsonify(error=str(e)), 400

    try:
        PostService.update_post(post_id, g.uid, update_fields)
        response = {"message": "Post updated"}
        if image_url is not None:              
            response["image_url"] = image_url
        return jsonify(response), 200
    except ValueError as ve:
        return jsonify(error=str(ve)), 400
    except Exception as e:
        return jsonify(error=str(e)), 500

@posts_bp.route("/posts/<post_id>", methods=["DELETE"])
@auth_required
def delete_post(post_id):
    """Delete post endpoint for regular users - can only delete their own posts"""
    try:
        PostService.delete_post_for_user(post_id, g.uid)
        return jsonify(message="Post deleted"), 200
    except ValueError as ve:
        return jsonify(error=str(ve)), 400
    except Exception as e:
        return jsonify(error=str(e)), 500

@posts_bp.route("/admin/posts/<post_id>", methods=["DELETE"])
@admin_required
def admin_delete_post(post_id):
    """Delete post endpoint for admins - can delete any post"""
    try:
        PostService.delete_post_for_admin(post_id)
        return jsonify(message="Post deleted by admin"), 200
    except ValueError as ve:
        return jsonify(error=str(ve)), 400
    except Exception as e:
        return jsonify(error=str(e)), 500

@posts_bp.route("/posts", methods=["GET"])
def get_posts():
    try:
        posts = PostService.get_posts()  # No uid
        allowed_fields = [
            "author_name", "created_at", "image_url", "status",
            "notes", "missing_name", "missing_age", "last_seen", "id"
        ]
        filtered_posts = [
            {k: post.get(k) for k in allowed_fields if k in post}
            for post in posts
        ]
        return jsonify(posts=filtered_posts), 200
    except Exception as e:
        return jsonify(error=str(e)), 500

@posts_bp.route("/posts/<post_id>", methods=["GET"])
def get_post(post_id):
    try:
        post = PostService.get_post(post_id)  # No uid
        if not post:
            return jsonify(error="Post not found"), 404
        allowed_fields = [
            "author_name", "created_at", "image_url", "status",
            "notes", "missing_name", "missing_age", "last_seen", "id"
        ]
        filtered_post = {k: post.get(k) for k in allowed_fields if k in post}
        return jsonify(post=filtered_post), 200
    except Exception as e:
        return jsonify(error=str(e)), 500

@posts_bp.route("/posts/<post_id>/report", methods=["POST"])
@auth_required
def report_post(post_id):
    reason = (request.get_json() or {}).get("reason", "")
    db.collection("post_reports").document(post_id).set({
        "reporter": g.uid,
        "reason": reason[:200],
        "created_at": firestore.SERVER_TIMESTAMP,
    })
    return jsonify(message="reported"), 201
@posts_bp.route("/search", methods=["POST"])
@auth_required
def search_for_missing():
    """
    Upload a query photo and compare it against all *missing-person* posts.
    Returns a list of matches sorted by ascending distance.
    """
    if "image_file" not in request.files:
        return jsonify(error="image_file is required"), 400

    search_image_bytes = request.files["image_file"].read()

    try:
        # 1) pull every post doc (already sorted newest→oldest)
        all_posts = PostService.get_posts()
        best_match = None
        best_distance = None

        for post in all_posts:
            # skip posts that are NOT 'missing'
            if post.get("post_type") != "missing":
                continue

            img_url = post.get("image_url")
            if not img_url:
                continue

            try:
                resp = requests.get(img_url, timeout=5)
                resp.raise_for_status()
                post_image_bytes = resp.content
            except Exception as e:
                # network error or bad URL – skip this post
                print(f"[search] skip {post.get('id')}: {e}")
                continue

            # 2) compare query image to post image
            distance = face_service.compare_faces(search_image_bytes, post_image_bytes)

            # 3) keep only strong matches (threshold may need tuning)
            if distance < 0.4:
                if best_distance is None or distance < best_distance:
                    best_distance = distance
                    best_match = {
                        "post_id": post.get("id"),
                        "distance": float(distance),
                        "post_details": post
                    }
        if best_match:
            return jsonify(matches=[best_match]), 200
        else:
            return jsonify(matches=[]), 200

    except ValueError as ve:
        return jsonify(error=str(ve)), 400
    except Exception as e:
        return jsonify(error=str(e)), 500