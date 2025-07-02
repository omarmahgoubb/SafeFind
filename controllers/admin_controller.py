# controllers/admin_controller.py
from flask import Blueprint, request, jsonify
from services.admin_service import AdminService
from controllers.auth_decorators import *
from services.admin_service import AdminService          
from controllers.auth_decorators import admin_required   
from services.posts_service import PostService
from config import db  # or wherever you initialize Firestore



admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

# 1.1 view all users  ─────────────────────────────
@admin_bp.route("/users", methods=["GET"])
@admin_required
def list_users():
    cursor = request.args.get("cursor")     # pagination
    users, next_cursor = AdminService.list_users(cursor)
    return jsonify(users=users, next_cursor=next_cursor), 200

# 1.2 suspend / unsuspend  ───────────────────────
@admin_bp.route("/users/<uid>/status", methods=["PATCH"])
@admin_required
def change_user_status(uid):
    body = request.get_json() or {}
    suspended = bool(body.get("suspend"))
    AdminService.set_user_disabled(uid, suspended)
    return jsonify(message="updated", suspended=suspended), 200

# 1.3 review reported posts  ─────────────────────
@admin_bp.route("/reports", methods=["GET"])
@admin_required
def list_reports():
    reports = AdminService.list_reports(limit=100)
    return jsonify(reports=reports), 200

# 1.4 delete a post  ─────────────────────────────
@admin_bp.route("/posts/<post_id>", methods=["DELETE"])
@admin_required
def delete_post(post_id):
    AdminService.delete_post(post_id)
    return jsonify(message="post deleted"), 200

# 1.5 get user count  ────────────────────────────
@admin_bp.route("/users/count", methods=["GET"])
@admin_required
def user_count():
    total = AdminService.get_user_count()
    return jsonify(total_users=total), 200

# 1.6 get found post count  ─────────────────────
@admin_bp.route("/posts/found/count", methods=["GET"])
@admin_required
def found_post_count():
    total = PostService.get_found_post_count()
    return jsonify(total_found_posts=total), 200

# 1.7 get reported post count  ───────────────────
@admin_bp.route("/posts/reported/count", methods=["GET"])
@admin_required
def reported_post_count():
    total = PostService.get_reported_post_count()
    return jsonify(total_reported_posts=total), 200

# 1.8 get successful match count  ─────────────────
@admin_bp.route("/matches/successful/count", methods=["GET"])
@admin_required
def successful_matches_count():
    stats = db.collection("match_stats").where("success", "==", True).stream()
    count = sum(1 for _ in stats)
    return jsonify(successful_matches=count), 200

# 1.9 get unsuccessful match count  ────────────────
@admin_bp.route("/matches/unsuccessful/count", methods=["GET"])
@admin_required
def unsuccessful_matches_count():
    stats = db.collection("match_stats").where("success", "==", False).stream()
    count = sum(1 for _ in stats)
    return jsonify(unsuccessful_matches=count), 200