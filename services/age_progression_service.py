import logging
import uuid
import requests
from io import BytesIO
from urllib.parse import urlparse, unquote
from PIL import Image
from firebase_admin import storage

from services.face_recognition_service import FaceRecognitionService
from services.posts_service        import PostService

logger = logging.getLogger("AgeProgressionService")


class AgeProgressionService:
    def __init__(self):
        self.colab_service_url = "https://cd01-34-124-246-58.ngrok-free.app"
        self.face_service = FaceRecognitionService()

    def progress_age_and_search(self, image_input, target_age: int) -> dict:

        try:
            # 1) get original bytes
            if isinstance(image_input, (bytes, bytearray)):
                orig_bytes = image_input
            else:
                orig_bytes = self._download_image(image_input)

            # 2) resize for the model
            proc = self._resize(orig_bytes, (512, 512))

            # 3) call your FastAPI age model
            aged_bytes = self._call_colab_service(proc, target_age)

            # 4) upload aged image back to Firebase
            aged_url = self._upload(aged_bytes, "age_progressed", f"age_{target_age}")

            posts = PostService.get_posts()
            candidates = []
            for post in posts:
                if post.post_type != "missing":
                    continue
                try:
                    other = self._download_image(post.image_url)
                    dist  = self.face_service.compare_faces(aged_bytes, other)
                except Exception:
                    continue
                if dist < FaceRecognitionService.THRESHOLD:
                    candidates.append({
                        "post_id":      post.id,
                        "distance":     dist,
                        "image_url":    post.image_url,
                        "post_details": post.to_dict(),
                    })

            if candidates:
                best = min(candidates, key=lambda x: x["distance"])
                return {"aged_image_url": aged_url, "closest_match": best}
            else:
                return {"aged_image_url": aged_url, "message": "No match found"}

        except Exception:
            logger.exception("Age progression + search failed")
            raise

    def _download_image(self, url: str) -> bytes:
        bucket = storage.bucket()
        p = urlparse(url)
        blob = None

        if "/o/" in p.path:
            blob = unquote(p.path.split("/o/")[1])
        else:
            path = p.path.lstrip("/")
            if path.startswith(bucket.name + "/"):
                blob = path[len(bucket.name) + 1 :]

        if blob:
            return bucket.blob(blob).download_as_bytes()

        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.content

    def _resize(self, img_bytes: bytes, size: tuple[int,int]) -> bytes:
        img = Image.open(BytesIO(img_bytes)).convert("RGB")
        img.thumbnail(size, Image.Resampling.LANCZOS)
        buf = BytesIO()
        img.save(buf, format="JPEG")
        return buf.getvalue()

    def _upload(self, img_bytes: bytes, folder: str, subfolder: str) -> str:
        bucket = storage.bucket()
        path   = f"{folder}/{subfolder}/{uuid.uuid4()}.jpg"
        blob   = bucket.blob(path)
        blob.upload_from_string(img_bytes, content_type="image/jpeg")
        blob.make_public()
        return blob.public_url

    def _call_colab_service(self, img_bytes: bytes, target_age: int) -> bytes:
        files = {"image": ("input.jpg", img_bytes, "image/jpeg")}
        data  = {"target_age": str(target_age)}
        url   = f"{self.colab_service_url}/age-transform"
        r     = requests.post(url, files=files, data=data, timeout=30)
        r.raise_for_status()
        return r.content
