from flask import Blueprint, request, jsonify
import requests
from services.auth_service import AuthService
from controllers.auth_decorators import auth_required
from schemas.auth_schema import RegisterSchema, LoginSchema, UpdateProfileSchema
from pydantic import ValidationError

auth_bp = Blueprint("auth", __name__)

# -------------------------- REGISTER ------------------------------
@auth_bp.route("/register", methods=["POST"])
def register():
    try:
        data = RegisterSchema(**(request.get_json() or {}))
    except ValidationError as e:
        return jsonify(e.errors()), 400

    valid, msg = AuthService.validate_registration(
        data.email, data.password, data.phone, data.photo_url, data.gender
    )
    if not valid:
        return jsonify(error=msg), 400

    try:
        uid = AuthService.register_user(
            data.email, data.password, data.first_name, data.last_name,
            data.phone, data.photo_url, data.gender  # Pass gender here
        )
        return jsonify(message="Registration successful", uid=uid), 201
    except Exception as e:
        return jsonify(error=str(e)), 400

# ---------------------------- LOGIN -------------------------------
@auth_bp.route("/login", methods=["POST"])
def login():
    try:
        data = LoginSchema(**(request.get_json(silent=True) or request.form.to_dict()))
    except ValidationError as e:
        return jsonify(e.errors()), 400

    try:
        result = AuthService.login_user(data.email, data.password)
        return jsonify(message="Login successful", **result), 200
    except requests.HTTPError as http_err:
        return jsonify(error=http_err.response.json()), http_err.response.status_code
    except Exception as e:
        return jsonify(error=str(e)), 500

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


