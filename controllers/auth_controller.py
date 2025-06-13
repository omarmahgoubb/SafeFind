from flask import Blueprint, request, jsonify
import requests
from services.auth_service import AuthService
from controllers.auth_decorators import auth_required


auth_bp = Blueprint("auth", __name__)

# -------------------------- REGISTER ------------------------------
@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json() or {}
    for field in ("email", "password", "first_name", "last_name", "phone"):
        if not data.get(field):
            return jsonify(error=f"{field} is required"), 400

    email = data["email"].lower().strip()
    password = data["password"]
    first = data["first_name"].strip()
    last = data["last_name"].strip()
    phone = data["phone"].strip()
    photo_url = (data.get("photo_url") or "").strip()

    valid, msg = AuthService.validate_registration(email, password, phone, photo_url)
    if not valid:
        return jsonify(error=msg), 400

    try:
        uid = AuthService.register_user(email, password, first, last, phone, photo_url or None)
        return jsonify(message="Registration successful", uid=uid), 201
    except Exception as e:
        return jsonify(error=str(e)), 400

# ---------------------------- LOGIN -------------------------------
@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or request.form.to_dict()
    email = (data.get("email") or "").lower().strip()
    password = data.get("password", "")

    if not email or not password:
        return jsonify(error="Email and password required"), 400

    try:
        result = AuthService.login_user(email, password)
        return jsonify(message="Login successful", **result), 200
    except requests.HTTPError as http_err:
        return jsonify(error=http_err.response.json()), http_err.response.status_code
    except Exception as e:
        return jsonify(error=str(e)), 500

# ------------------------- UPDATE PROFILE -------------------------
@auth_bp.route("/update-profile", methods=["PATCH"])
@auth_required
def update_profile():
    data = request.get_json() or {}
    updates = {}
    for field in ("first_name", "last_name", "phone", "photo_url"):
        if field in data:
            updates[field] = data[field].strip()
    if not updates:
        return jsonify({"error": "No valid fields to update"}), 400
    try:
        AuthService.update_profile(request.uid, updates)
        return jsonify(message="Profile updated", updated=updates), 200
    except Exception as e:
        return
# ---------------------------- GET ME ------------------------------
@auth_bp.route("/me", methods=["GET"])
@auth_required
def get_me():
    """Return the signed‑in user’s full profile."""
    try:
        profile = AuthService.get_user_profile(request.uid)
        return jsonify(profile), 200
    except Exception as e:
        return jsonify(error=str(e)), 500