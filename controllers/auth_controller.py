import uuid, os
from flask import Blueprint, request, jsonify
from firebase_admin import storage
from services.auth_service import AuthService
from controllers.auth_decorators import auth_required
from schemas.auth_schema import RegisterSchema, LoginSchema, UpdateProfileSchema
from pydantic import ValidationError

auth_bp = Blueprint("auth", __name__)

# -------------------------- REGISTER ------------------------------
@auth_bp.route("/register", methods=["POST"])
def register():
    # 1) If a file was uploaded under "photo_url", push it to Firebase Storage
    photo_url = ""
    if "photo_url" in request.files:
        file = request.files["photo_url"]
        ext  = os.path.splitext(file.filename)[1]
        blob_name = f"users/{uuid.uuid4()}{ext}"
        bucket = storage.bucket()
        blob   = bucket.blob(blob_name)
        blob.upload_from_file(file, content_type=file.mimetype)
        blob.make_public()
        photo_url = blob.public_url

    # 2) Merge that URL into the rest of the form-data
    form = request.form.to_dict()
    form["photo_url"] = photo_url

    # 3) Validate via Pydantic
    try:
        data = RegisterSchema(**form)
    except ValidationError as e:
        return jsonify(e.errors()), 400

    # 4) Business-logic validation
    valid, msg = AuthService.validate_registration(
        data.email, data.password, data.phone, data.photo_url
    )
    if not valid:
        return jsonify(error=msg), 400

    # 5) Create user
    try:
        uid = AuthService.register_user(
            data.email,
            data.password,
            data.first_name,
            data.last_name,
            data.phone,
            data.photo_url
        )
        return jsonify(message="Registration successful", uid=uid), 201
    except Exception as e:
        return jsonify(error=str(e)), 400


# ---------------------------- LOGIN -------------------------------
@auth_bp.route("/login", methods=["POST"])
def login():
    # accept either JSON or form-data
    raw = request.get_json(silent=True) or request.form.to_dict()
    try:
        data = LoginSchema(**raw)
    except ValidationError as e:
        return jsonify(e.errors()), 400

    try:
        result = AuthService.login_user(data.email, data.password)
        return jsonify(message="Login successful", **result), 200
    except Exception as e:
        return jsonify(error=str(e)), getattr(e, "status_code", 500)


# ------------------------- UPDATE PROFILE -------------------------
@auth_bp.route("/update-profile", methods=["PATCH"])
@auth_required
def update_profile():
    try:
        updates = UpdateProfileSchema(**(request.get_json() or {})).dict(exclude_unset=True)
    except ValidationError as e:
        return jsonify(e.errors()), 400

    if not updates:
        return jsonify({"error": "No valid fields to update"}), 400

    try:
        AuthService.update_profile(request.uid, updates)
        return jsonify(message="Profile updated", updated=updates), 200
    except Exception as e:
        return jsonify(error=str(e)), 500


# ---------------------------- GET ME ------------------------------
@auth_bp.route("/me", methods=["GET"])
@auth_required
def get_me():
    try:
        user = AuthService.get_user_profile(request.uid)
        return jsonify(user.to_dict()), 200
    except Exception as e:
        return jsonify(error=str(e)), 500
