import re
import requests
from firebase_admin import auth as fb_auth, firestore
from config import FIREBASE_API_KEY
from repositories.user_repository import UserRepository
from models.user_model import User
from paths import FIREBASE_STORAGE_BUCKET_URL_PREFIX

EMAIL_REGEX = re.compile(r"^[^@]+@[^@]+\.[^@]+$")
PHONE_REGEX = re.compile(r"^\+?\d{10,15}$")

BUCKET_URL_PREFIX = FIREBASE_STORAGE_BUCKET_URL_PREFIX


class AuthService:

    # --------------------------- validation ---------------------------
    @staticmethod
    def validate_registration(email: str, password: str, phone: str, photo_url: str = ""):
        if not EMAIL_REGEX.match(email):
            return False, "Invalid email format"
        if len(password) < 8:
            return False, "Password must be at least 8 characters"
        if not PHONE_REGEX.match(phone):
            return False, "Invalid phone format"
        if photo_url and not photo_url.startswith(BUCKET_URL_PREFIX):
            return False, "photo_url must come from the project bucket"

        if UserRepository.get_user_by_email(email):
            return False, "Email already in use"

        if UserRepository.get_user_by_phone(phone):
            return False, "Phone already in use"

        return True, None

    # ---------------------------- create -----------------------------
    @staticmethod
    def register_user(email: str, password: str, first_name: str, last_name: str,
                      phone: str, photo_url: str | None = None) -> str:
        user_record = fb_auth.create_user(
            email=email,
            password=password,
            display_name=f"{first_name} {last_name}",
            photo_url=photo_url or None,
        )
        user_profile = User(
            uid=user_record.uid,
            email=email,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            photo_url=photo_url or "",
            role="user",
            created_at=firestore.SERVER_TIMESTAMP,
        )
        UserRepository.create_user_profile(user_record.uid, user_profile.to_dict())
        return user_record.uid

    # ----------------------------- login -----------------------------
    @staticmethod
    def login_user(email: str, password: str) -> dict:
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}"
        resp = requests.post(url, json={"email": email, "password": password, "returnSecureToken": True})
        resp.raise_for_status()
        data = resp.json()
        uid = data["localId"]

        doc = UserRepository.get_user_profile(uid)
        user = User.from_dict(uid, doc.to_dict()) if doc.exists else User(uid, email, "", "", "", "", "user", None)

        return {
            "uid": uid,
            "idToken": data["idToken"],
            "refreshToken": data["refreshToken"],
            "role": user.role,
            "photo_url": user.photo_url,
            "first_name": user.first_name,
            "last_name": user.last_name,
        }

    # ----------------------------- update ----------------------------
    @staticmethod
    def update_profile(uid: str, updates: dict):
        if "photo_url" in updates and not updates["photo_url"].startswith(BUCKET_URL_PREFIX):
            raise ValueError("photo_url must come from the project bucket")
        if "photo_url" in updates:
            UserRepository.update_firebase_user(uid, photo_url=updates["photo_url"] or None)
        if updates:
            UserRepository.update_user_profile(uid, updates)

    # ------------------------------ read -----------------------------
    @staticmethod
    def get_user_profile(uid: str) -> User:
        doc = UserRepository.get_user_profile(uid)
        if not doc.exists:
            raise ValueError("User not found")
        profile_data = doc.to_dict()
        auth_rec = fb_auth.get_user(uid)

        # Ensure all fields are present for User model initialization
        profile_data.setdefault("email", auth_rec.email)
        profile_data.setdefault("photo_url", auth_rec.photo_url or "")
        if "first_name" not in profile_data or "last_name" not in profile_data:
            parts = (auth_rec.display_name or "").split(" ")
            profile_data.setdefault("first_name", parts[0] if parts else "")
            profile_data.setdefault("last_name", " ".join(parts[1:]))
        profile_data.setdefault("role", "user")
        profile_data.setdefault("created_at", firestore.SERVER_TIMESTAMP)

        return User.from_dict(uid, profile_data)