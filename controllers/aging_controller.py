# controllers/aging_controller.py
import base64
from flask import Blueprint, request, jsonify, Response
from services.age_progression_service import AgeProgressionService

aging_bp = Blueprint("aging", __name__)
age_service = AgeProgressionService()

@aging_bp.route("/age-progress", methods=["POST"])
def age_progress():
    """
    Supports two modes:

      1) multipart/form-data:
           • key "image": file upload
           • key "target_age": text

      2) application/json:
           { "image_b64": "<base64 string>", "target_age": 50 }
    """
    # 1) multipart/form-data
    if request.content_type.startswith("multipart/form-data"):
        if "image" not in request.files or "target_age" not in request.form:
            return jsonify(error="image file and target_age required"), 400

        file = request.files["image"]
        try:
            target_age = int(request.form["target_age"])
        except ValueError:
            return jsonify(error="target_age must be an integer"), 400

        image_bytes = file.read()

    # 2) pure JSON + base64
    elif request.is_json:
        data = request.get_json()
        if "image_b64" not in data or "target_age" not in data:
            return jsonify(error="image_b64 and target_age required"), 400

        try:
            image_bytes = base64.b64decode(data["image_b64"])
        except Exception:
            return jsonify(error="invalid base64 image"), 400

        try:
            target_age = int(data["target_age"])
        except ValueError:
            return jsonify(error="target_age must be an integer"), 400

    else:
        return jsonify(error="Unsupported content type"), 415

    # now we have image_bytes and target_age
    try:
        # If you just want to return the raw JPEG bytes:
        processed_bytes = age_service._call_colab_service(image_bytes, target_age)
        return Response(processed_bytes, mimetype="image/jpeg")

        # Or, if you want to upload back to Firebase and return a URL:
        # url = age_service.upload_result(processed_bytes, "age_progressed", f"age_{target_age}")
        # return jsonify(progressed_url=url), 200

    except Exception as e:
        return jsonify(error=str(e)), 500