from flask import Blueprint, request, jsonify
from services.age_progression_service import AgeProgressionService
from services.posts_service import PostService

aging_bp = Blueprint("aging", __name__)
age_service = AgeProgressionService()


@aging_bp.route("/age-progress", methods=["POST"])
def age_progress():
    """
    Endpoint for age progression
    Request JSON: { "post_id": "abc123", "target_age": 50 }
    Response: { "progressed_url": "https://firebase/age_progressed.jpg" }
    """
    data = request.get_json()
    if not data or "post_id" not in data or "target_age" not in data:
        return jsonify(error="post_id and target_age are required"), 400

    try:
        # Get post using existing service
        post = PostService.get_post(data["post_id"])
        if not post:
            return jsonify(error="Post not found"), 404

        # Process image
        progressed_url = age_service.progress_age(post.image_url, data["target_age"])

        return jsonify(progressed_url=progressed_url), 200

    except ValueError as e:
        return jsonify(error=str(e)), 404
    except Exception as e:
        return jsonify(error=str(e)), 500