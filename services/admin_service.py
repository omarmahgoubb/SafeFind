from firebase_admin import auth as fb_auth, firestore
from google.cloud.firestore import Query
from services.posts_service import PostService

db = firestore.client()

class AdminService:

    # 2.1 paginate users (100 per page) -------------
    @staticmethod
    def list_users(cursor: str | None):
        page = fb_auth.list_users(page_token=cursor, max_results=100)
        users = [{
            "uid": u.uid,
            "email": u.email,
            "disabled": u.disabled,
            "name": u.display_name,
            "photo": u.photo_url
        } for u in page.users]
        return users, page.next_page_token

    # 2.2 suspend / unsuspend -----------------------
    @staticmethod
    def set_user_disabled(uid: str, disabled: bool):
        fb_auth.update_user(uid, disabled=disabled)
        db.collection("users").document(uid).update({"disabled": disabled})

    # 2.3 list reported posts -----------------------
    @staticmethod
    def list_reports(limit=100):
        docs = (db.collection("post_reports")
                  .order_by("created_at", direction=Query.DESCENDING)
                  .limit(limit).stream())
        return [d.to_dict() | {"doc_id": d.id} for d in docs]

    # 2.4 delete a post + cascading cleanup --------
    @staticmethod
    def delete_post(post_id: str):
        doc_ref = db.collection("posts").document(post_id)
        snapshot = doc_ref.get()
        if not snapshot.exists:
            raise ValueError("Post not found")

        data = snapshot.to_dict() or {}
        data.get("uid", "")
        PostService.delete_post_for_admin(post_id)

        db.collection("post_reports").document(post_id).delete()

