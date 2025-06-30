from datetime import datetime

class User:
    def __init__(self, uid: str, email: str, first_name: str, last_name: str, phone: str, photo_url: str, role: str, created_at):
        self.uid = uid
        self.email = email
        self.first_name = first_name
        self.last_name = last_name
        self.phone = phone
        self.photo_url = photo_url
        self.role = role
        self.created_at = created_at

    @staticmethod
    def from_dict(uid: str, source: dict):
        return User(
            uid,
            source.get("email"),
            source.get("first_name"),
            source.get("last_name"),
            source.get("phone"),
            source.get("photo_url"),
            source.get("role", "user"),
            source.get("created_at"),
        )

    def to_dict(self):
        return {
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "phone": self.phone,
            "photo_url": self.photo_url,
            "role": self.role,
            "created_at": self.created_at,
        }

    def is_owner(self, current_uid: str) -> bool:
        return self.uid == current_uid

    def get_full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    def get_created_at_iso(self) -> str:
        if self.created_at and hasattr(self.created_at, "to_datetime"):
            return self.created_at.to_datetime().isoformat()
        elif isinstance(self.created_at, datetime):
            return self.created_at.isoformat()
        return ""


