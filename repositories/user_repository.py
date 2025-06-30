from config import db
from firebase_admin import auth as fb_auth

class UserRepository:
    @staticmethod
    def get_user_by_email(email: str):
        users = db.collection("users").where("email", "==", email).limit(1).stream()
        return next(users, None)

    @staticmethod
    def get_user_by_phone(phone: str):
        users = db.collection("users").where("phone", "==", phone).limit(1).stream()
        return next(users, None)

    @staticmethod
    def create_user_profile(uid: str, profile_data: dict):
        db.collection("users").document(uid).set(profile_data)

    @staticmethod
    def get_user_profile(uid: str):
        return db.collection("users").document(uid).get()

    @staticmethod
    def update_user_profile(uid: str, updates: dict):
        db.collection("users").document(uid).update(updates)

    @staticmethod
    def update_firebase_user(uid: str, **kwargs):
        fb_auth.update_user(uid, **kwargs)

    @staticmethod
    def get_user_count() -> int:
        snap = db.collection("users").count().get()   # alias optional
        return snap[0][0].value if snap else 0