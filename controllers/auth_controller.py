from flask import Blueprint, request, jsonify
from services.auth_service import AuthService
import requests

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    for field in ('email','password','first_name','last_name','phone'):
        if not data.get(field):
            return jsonify(error=f"{field} is required"), 400

    email   = data['email'].lower().strip()
    password= data['password']
    first   = data['first_name'].strip()
    last    = data['last_name'].strip()
    phone   = data['phone'].strip()

    valid, msg = AuthService.validate_registration(email, password, phone)
    if not valid:
        return jsonify(error=msg), 400

    try:
        uid = AuthService.register_user(email, password, first, last, phone)
        return jsonify(message="Registration successful", uid=uid), 201
    except Exception as e:
        return jsonify(error=str(e)), 400

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or request.form.to_dict()
    email    = (data.get('email') or "").lower().strip()
    password = data.get('password','')

    if not email or not password:
        return jsonify(error="Email and password required"), 400

    try:
        result = AuthService.login_user(email, password)
        return jsonify(message="Login successful", **result), 200
    except requests.HTTPError as http_err:
        return jsonify(error=http_err.response.json()), http_err.response.status_code
    except Exception as e:
        return jsonify(error=str(e)), 500

@auth_bp.route('/update-profile', methods=['PATCH'])
def update_profile():
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return jsonify({"error": "Missing auth token"}), 401

    id_token = auth_header.split(" ",1)[1]
    from firebase_admin import auth as firebase_auth
    try:
        claims = firebase_auth.verify_id_token(id_token)
        uid = claims["uid"]
    except Exception:
        return jsonify({"error": "Invalid or expired token"}), 401

    data = request.get_json() or {}
    updates = {}

    for field in ('first_name','last_name','phone'):
        if field in data:
            updates[field] = data[field].strip()

    if not updates:
        return jsonify({"error": "No valid fields to update"}), 400

    AuthService.update_profile(uid, updates)
    return jsonify(message="Profile updated", updated=updates), 200
