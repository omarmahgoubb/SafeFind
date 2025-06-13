from functools import wraps
from flask import request, jsonify
from firebase_admin import auth as firebase_auth
from config import db

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing auth token"}), 401

        id_token = auth_header.split(" ", 1)[1]
        try:
            claims = firebase_auth.verify_id_token(id_token)
            uid = claims["uid"]
        except Exception:
            return jsonify({"error": "Invalid or expired token"}), 401

        user_doc = db.collection("users").document(uid).get()
        if not user_doc.exists or user_doc.to_dict().get("role") != "admin":
            return jsonify({"error": "Forbidden"}), 403

        return fn(*args, **kwargs)
    return wrapper

def auth_required(fn):
    """Decorator that injects request.uid when the ID token is valid."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing auth token"}), 401
        id_token = auth_header.split(" ", 1)[1]
        try:
            claims = firebase_auth.verify_id_token(id_token)
            request.uid = claims["uid"]
        except Exception:
            return jsonify({"error": "Invalid or expired token"}), 401
        return fn(*args, **kwargs)
    return wrapper