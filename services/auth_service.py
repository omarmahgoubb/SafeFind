import re
import requests
from datetime import datetime
from firebase_admin import auth as fb_auth, firestore
from config import db, FIREBASE_API_KEY
from firebase_admin import get_app


EMAIL_REGEX = re.compile(r"^[^@]+@[^@]+\.[^@]+$")
PHONE_REGEX = re.compile(r"^\+?\d{10,15}$")

BUCKET_URL_PREFIX = (
    "https://firebasestorage.googleapis.com/v0/b/"
    + get_app().options.get("storageBucket")      
)

class AuthService:
    """Wrapper around Firebase Auth & Firestore with optional avatars."""

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

    # existing phone-uniqueness check
        if any(db.collection("users")
           .where("phone", "==", phone)
           .limit(1)
           .stream()):
            return False, "Phone already in use"

        return True, None

    # ---------------------------- create -----------------------------
    @staticmethod
    def register_user(email: str, password: str, first_name: str, last_name: str,
                       phone: str, photo_url: str | None = None) -> str:
        user = fb_auth.create_user(
            email=email,
            password=password,
            display_name=f"{first_name} {last_name}",
            photo_url=photo_url or None,
        )
        profile = {
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "phone": phone,
            "photo_url": photo_url or "",
            "role": "user",
            "created_at": firestore.SERVER_TIMESTAMP,
        }
        db.collection("users").document(user.uid).set(profile)
        return user.uid

    # ----------------------------- login -----------------------------
    @staticmethod
    def login_user(email: str, password: str) -> dict:
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}"
        resp = requests.post(url, json={"email": email, "password": password, "returnSecureToken": True})
        resp.raise_for_status()
        data = resp.json()
        uid = data["localId"]

        doc = db.collection("users").document(uid).get()
        role = photo = first = last = ""
        if doc.exists:
            d = doc.to_dict()
            role = d.get("role", "user")
            photo = d.get("photo_url", "")
            first = d.get("first_name", "")
            last = d.get("last_name", "")

        return {
            "uid": uid,
            "idToken": data["idToken"],
            "refreshToken": data["refreshToken"],
            "role": role or "user",
            "photo_url": photo,
            "first_name": first,
            "last_name": last,
        }

    # ----------------------------- update ----------------------------
    @staticmethod
    def update_profile(uid: str, updates: dict):
        if "photo_url" in updates and not updates["photo_url"].startswith(BUCKET_URL_PREFIX):
            raise ValueError("photo_url must come from the project bucket")
        if "photo_url" in updates:
            fb_auth.update_user(uid, photo_url=updates["photo_url"] or None)
        if updates:
            db.collection("users").document(uid).update(updates)

    # ------------------------------ read -----------------------------
    @staticmethod
    def get_user_profile(uid: str) -> dict:
        doc = db.collection("users").document(uid).get()
        profile = doc.to_dict() if doc.exists else {}
        if profile is None:
            profile = {}
        auth_rec = fb_auth.get_user(uid)
        profile.setdefault("email", auth_rec.email)
        profile.setdefault("photo_url", auth_rec.photo_url or "")
        if "first_name" not in profile or "last_name" not in profile:
            parts = (auth_rec.display_name or "").split(" ")
            profile.setdefault("first_name", parts[0] if parts else "")
            profile.setdefault("last_name", " ".join(parts[1:]))
        ts = profile.get("created_at")
        if ts and hasattr(ts, "to_datetime"):
            profile["created_at"] = ts.to_datetime().isoformat()
        elif isinstance(ts, datetime):
            profile["created_at"] = ts.isoformat()
        return profile