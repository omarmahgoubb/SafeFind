from firebase_admin import auth as fb_auth, firestore
from google.cloud.firestore import Query
from services.posts_service import PostService
from repositories.user_repository import UserRepository 

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
        docs = (
            db.collection("post_reports")
            .order_by("created_at", direction=Query.DESCENDING)
            .limit(limit)
            .stream()
        )
        out = []
        for d in docs:
            rec = d.to_dict()
            rec["doc_id"] = d.id
            # rec["post_id"] is already in the document now
            out.append(rec)
        return out

    # 2.4 delete a post + cascading cleanup --------
    @staticmethod
    def delete_post(post_id: str):
        # Use the new admin deletion method from PostService
        PostService.delete_post_for_admin(post_id)

        # clean up any report doc
        reports = db.collection("post_reports") \
            .where("post_id", "==", post_id) \
            .stream()
        for rpt in reports:
            rpt.reference.delete()

    @staticmethod
    def get_user_count() -> int:
        return UserRepository.get_user_count()