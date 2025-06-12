import re
import requests
from firebase_admin import auth as fb_auth, firestore
from config import db, FIREBASE_API_KEY

EMAIL_REGEX = re.compile(r'^[^@]+@[^@]+\.[^@]+$')
PHONE_REGEX = re.compile(r'^\+?\d{10,15}$')

class AuthService:
    @staticmethod
    def validate_registration(email, password, phone):
        if not EMAIL_REGEX.match(email):
            return False, "Invalid email format"
        if len(password) < 8:
            return False, "Password must be at least 8 characters"
        if not PHONE_REGEX.match(phone):
            return False, "Invalid phone format"
        docs = db.collection("users").where("phone", "==", phone).limit(1).stream()
        if any(docs):
                return False, f"{field.capitalize()} already in use"
        return True, None

    @staticmethod
    def register_user(email, password, first_name, last_name, phone):
        user = fb_auth.create_user(email=email, password=password)
        profile = {
            "email":      email,
            "first_name": first_name,
            "last_name":  last_name,
            "phone":      phone,
            "role":       "user",
            "created_at": firestore.SERVER_TIMESTAMP
        }
        db.collection("users").document(user.uid).set(profile)
        return user.uid

    @staticmethod
    def login_user(email, password):
        url = (
            "https://identitytoolkit.googleapis.com/v1/"
            f"accounts:signInWithPassword?key={FIREBASE_API_KEY}"
        )
        payload = {"email": email, "password": password, "returnSecureToken": True}
        resp = requests.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        uid = data["localId"]
        doc = db.collection("users").document(uid).get()
        role = doc.to_dict().get("role", "user") if doc.exists else "user"
        return {
            "uid":          uid,
            "idToken":      data["idToken"],
            "refreshToken": data["refreshToken"],
            "role":         role
        }

    @staticmethod
    def update_profile(uid: str, updates: dict):
        db.collection("users").document(uid).update(updates)