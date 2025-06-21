from flask import Blueprint, request, jsonify
from controllers.auth_decorators import auth_required   # already exists :contentReference[oaicite:4]{index=4}
from services.auth_service import AuthService           # for user profile :contentReference[oaicite:5]{index=5}
from services.posts_service import PostService

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

    # pull signed-in user’s name
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
