from datetime import datetime

class Post:
    def __init__(self, id: str, uid: str, author_name: str, post_type: str, image_url: str, created_at, status: str, payload: dict):
        self.id = id
        self.uid = uid
        self.author_name = author_name
        self.post_type = post_type
        self.image_url = image_url
        self.created_at = created_at
        self.status = status
        self.payload = payload

    @staticmethod
    def from_dict(id: str, source: dict):
        return Post(
            id,
            source.get("uid"),
            source.get("author_name"),
            source.get("post_type"),
            source.get("image_url"),
            source.get("created_at"),
            source.get("status"),
            {
                "missing_name": source.get("missing_name"),
                "missing_age": source.get("missing_age"),
                "last_seen": source.get("last_seen"),
                "notes": source.get("notes"),
                "found_name": source.get("found_name"),
                "estimated_age": source.get("estimated_age"),
                "found_location": source.get("found_location"),
            }
        )

    def to_dict(self):
        data = {
            "uid": self.uid,
            "author_name": self.author_name,
            "post_type": self.post_type,
            "image_url": self.image_url,
            "created_at": self.created_at,
            "status": self.status,
        }
        data.update(self.payload)
        return data

    def get_created_at_iso(self) -> str:
        if self.created_at and hasattr(self.created_at, "to_datetime"):
            return self.created_at.to_datetime().isoformat()
        elif isinstance(self.created_at, datetime):
            return self.created_at.isoformat()
        return ""


