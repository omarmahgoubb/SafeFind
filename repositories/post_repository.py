from config import db
from firebase_admin import firestore


# The PostRepository class provides static methods
# to interact with post data stored in a Firestore database.
# It acts as a data access layer for post-related operations.
class PostRepository:
    @staticmethod
    def create_post(post_id: str, data: dict):
        db.collection("posts").document(post_id).set(data)

    @staticmethod
    def get_post_by_id(post_id: str):
        return db.collection("posts").document(post_id).get()

    @staticmethod
    def update_post(post_id: str, updates: dict):
        db.collection("posts").document(post_id).update(updates)

    @staticmethod
    def delete_post(post_id: str):
        db.collection("posts").document(post_id).delete()

    @staticmethod
    def get_all_posts():
        return db.collection("posts").order_by("created_at", direction=firestore.Query.DESCENDING).stream()

    @staticmethod
    def delete_post_report(post_id: str):
        db.collection("post_reports").document(post_id).delete()


