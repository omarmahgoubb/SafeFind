from flask import Blueprint, request, jsonify
from controllers.auth_decorators import auth_required, admin_required   # already exists
from services.auth_service import AuthService           # for user profile
from services.posts_service import PostService
from firebase_admin import firestore
from config import db

posts_bp = Blueprint("posts", __name__)

@posts_bp.route("/posts", methods=["POST"])
@auth_required
def create_post():
    if "image_file" not in request.files:
        return jsonify(error="image_file is required"), 400

    # basic form validation
    form = request.form.to_dict()
    for fld in ("missing_name", "missing_age", "last_seen"):
        if not form.get(fld):
            return jsonify(error=f"{fld} is required"), 400

    # pull signed-in user's name
    profile = AuthService.get_user_profile(request.uid)
    author = f"{profile.get('first_name','')} {profile.get('last_name','')}".strip()

    try:
        post_id, url = PostService.create_post(
            request.uid,
            author,
            {
              "missing_name": form["missing_name"],
              "missing_age": int(form["missing_age"]),
              "last_seen": form["last_seen"],
              "notes": form.get("notes", "")
            },
            request.files["image_file"],
        )
        return jsonify(message="Post created", post_id=post_id, image_url=url), 201
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
        try:
            image_url = PostService._upload_image(request.files["image_file"], request.uid)
            update_fields["image_url"] = image_url
        except Exception as e:
            return jsonify(error=str(e)), 400

    try:
        PostService.update_post(post_id, request.uid, update_fields)
        response = {"message": "Post updated"}
        if image_url is not None:              # file was supplied & passed validation
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
        PostService.delete_post_for_user(post_id, request.uid)
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
        "reporter": request.uid,
        "reason": reason[:200],
        "created_at": firestore.SERVER_TIMESTAMP,
    })
    return jsonify(message="reported"), 201

