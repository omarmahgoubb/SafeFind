import uuid, io
from abc import ABC, abstractmethod
from firebase_admin import storage
from services.image_service import preprocess

class ImageUploader(ABC):
    @abstractmethod
    def upload(self, file_storage, uid: str) -> str:
        pass

class MissingPostImageUploader(ImageUploader):
    def upload(self, file_storage, uid: str) -> str:
        raw = file_storage.read()
        clean_bytes, _ = preprocess(raw)
        blob_path = f"missing_posts/{uid}/{uuid.uuid4()}.jpg"
        blob = storage.bucket().blob(blob_path)
        blob.upload_from_file(io.BytesIO(clean_bytes),
                              content_type="image/jpeg")
        blob.make_public()
        return blob.public_url

class FoundPostImageUploader(ImageUploader):
    def upload(self, file_storage, uid: str) -> str:
        raw = file_storage.read()
        clean_bytes, _ = preprocess(raw)
        blob_path = f"found_posts/{uuid.uuid4()}.jpg"
        blob = storage.bucket().blob(blob_path)
        blob.upload_from_file(io.BytesIO(clean_bytes),
                              content_type="image/jpeg")
        blob.make_public()
        return blob.public_url

class ImageUploaderFactory:
    @staticmethod
    def get_uploader(post_type: str) -> ImageUploader:
        if post_type == "missing":
            return MissingPostImageUploader()
        elif post_type == "found":
            return FoundPostImageUploader()
        else:
            raise ValueError("Invalid post type for image uploader")


