# auth_decorators.py
from functools import wraps
from flask import request, jsonify
from firebase_admin import auth as firebase_auth
from config import db


def auth_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify(error="Missing auth token"), 401

        id_token = auth_header.split(" ", 1)[1]
        try:
            claims = firebase_auth.verify_id_token(id_token)
        except Exception:
            return jsonify(error="Invalid or expired token"), 401

        request.uid  = claims["uid"]
        request.role = claims.get("role")

        if request.role is None:
            doc = db.collection("users").document(request.uid).get()
            if doc.exists:
                request.role = doc.to_dict().get("role")

        return fn(*args, **kwargs)
    return wrapper


def admin_required(fn):
    @wraps(fn)
    @auth_required
    def wrapper(*args, **kwargs):
        if request.role != "admin":
            return jsonify(error="Forbidden"), 403
        return fn(*args, **kwargs)
    return wrapper
