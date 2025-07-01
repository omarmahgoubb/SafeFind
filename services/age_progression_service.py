import logging
import requests
import uuid
from firebase_admin import storage
from urllib.parse import urlparse, unquote
from io import BytesIO
from PIL import Image

logger = logging.getLogger("AgeProgressionService")


class AgeProgressionService:
    def __init__(self):
        # hard-coded model-server URL (no need for an env var now)
        self.colab_service_url = "https://593e-35-230-18-68.ngrok-free.app"

    def progress_age(self, image_url: str, target_age: int) -> str:
        """
        Download a Firebase-hosted image, send it to the aging service,
        then upload and return the URL of the aged image.
        """
        try:
            # 1) fetch bytes from Firebase or HTTP
            img_bytes = self.download_image(image_url)
            # 2) shrink to a reasonable size
            processed = self.resize_image(img_bytes, (512, 512))
            # 3) call the ngrok-exposed aging service
            result_bytes = self._call_colab_service(processed, target_age)
            # 4) upload result back to Firebase
            return self.upload_result(result_bytes, "age_progressed", f"age_{target_age}")
        except Exception as e:
            logger.error("Age progression failed", exc_info=True)
            raise RuntimeError("Age progression processing failed") from e

    def download_image(self, url: str) -> bytes:
        """
        Try to interpret URL as a Firebase Storage blob; if that fails,
        fall back to a normal HTTP GET.
        """
        bucket = storage.bucket()
        blob_name = None
        p = urlparse(url)

        # Firebase v1 URL style: /o/<encoded-path>?...
        if "/o/" in p.path:
            blob_name = unquote(p.path.split("/o/")[1])
        else:
            # older style: /<bucket-name>/<path>
            path = p.path.lstrip("/")
            if path.startswith(bucket.name + "/"):
                blob_name = path[len(bucket.name) + 1 :]

        if blob_name:
            return bucket.blob(blob_name).download_as_bytes()

        resp = requests.get(url)
        resp.raise_for_status()
        return resp.content

    def resize_image(self, image_bytes: bytes, size: tuple[int, int]) -> bytes:
        """Thumbnail the image to `size` while preserving aspect ratio."""
        img = Image.open(BytesIO(image_bytes)).convert("RGB")
        img.thumbnail(size, Image.Resampling.LANCZOS)
        buf = BytesIO()
        img.save(buf, format="JPEG")
        return buf.getvalue()

    def upload_result(self, image_bytes: bytes, folder: str, subfolder: str) -> str:
        """Upload to Firebase and return its public URL."""
        bucket = storage.bucket()
        path = f"{folder}/{subfolder}/{uuid.uuid4()}.jpg"
        blob = bucket.blob(path)
        blob.upload_from_string(image_bytes, content_type="image/jpeg")
        blob.make_public()
        return blob.public_url

    # expose this as the same name your controller expects:
    def _call_colab_service(self, img_bytes: bytes, target_age: int) -> bytes:
        return self._call_colab(img_bytes, target_age)

    # the real HTTP-POST against FastAPI
    def _call_colab(self, img_bytes: bytes, target_age: int) -> bytes:
        files = {"image": ("input.jpg", img_bytes, "image/jpeg")}
        data = {"target_age": str(target_age)}
        url = f"{self.colab_service_url}/age-transform"
        resp = requests.post(url, files=files, data=data, timeout=30)
        resp.raise_for_status()
        return resp.content