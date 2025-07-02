import base64
from flask import Blueprint, request, jsonify
from services.age_progression_service import AgeProgressionService

aging_bp = Blueprint("aging", __name__)
age_service = AgeProgressionService()

@aging_bp.route("/age-progress", methods=["POST"])
def age_progress():
    if request.content_type.startswith("multipart/form-data"):
        if "image" not in request.files or "target_age" not in request.form:
            return jsonify(error="image file and target_age required"), 400
        img_input = request.files["image"].read()
        try:
            age = int(request.form["target_age"])
        except ValueError:
            return jsonify(error="target_age must be integer"), 400

    elif request.is_json:
        js = request.get_json()
        if "image_b64" not in js or "target_age" not in js:
            return jsonify(error="image_b64 and target_age required"), 400
        try:
            img_input = base64.b64decode(js["image_b64"])
        except Exception:
            return jsonify(error="invalid base64"), 400
        try:
            age = int(js["target_age"])
        except ValueError:
            return jsonify(error="target_age must be integer"), 400

    else:
        return jsonify(error="unsupported content type"), 415

    try:
        result = age_service.progress_age_and_search(img_input, age)
        return jsonify(result), 200

    except Exception as e:
        return jsonify(error=str(e)), 500
