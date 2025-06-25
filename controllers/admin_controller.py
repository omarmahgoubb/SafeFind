# controllers/admin_controller.py
from flask import Blueprint
from services.admin_service import AdminService
from controllers.auth_decorators import *


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
    try:
        AdminService.delete_post(post_id)
        return jsonify(message="Post deleted"), 200
    except ValueError as ve:
        return jsonify(error=str(ve)), 404
    except Exception as e:
        return jsonify(error="Internal server error"), 500
