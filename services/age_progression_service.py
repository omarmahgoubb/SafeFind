import logging
import os
import requests
import uuid
from firebase_admin import storage
from urllib.parse import urlparse, unquote
from io import BytesIO
from PIL import Image

logger = logging.getLogger("AgeProgressionService")


class AgeProgressionService:
    def __init__(self):
        self.colab_service_url = os.getenv("COLAB_SERVICE_URL")

    def progress_age(self, image_url: str, target_age: int) -> str:
        """
        Progress age for an image stored in Firebase
        :param image_url: Firebase Storage URL of the input image
        :param target_age: Target age (20-70)
        :return: Firebase Storage URL of the processed image
        """
        try:
            # Download image using existing service logic
            image_bytes = self.download_image(image_url)

            # Resize for processing
            processed_bytes = self.resize_image(image_bytes, (512, 512))

            # Send to Colab service
            result_bytes = self._call_colab_service(processed_bytes, target_age)

            # Upload result to Firebase
            return self.upload_result(result_bytes, "age_progressed", f"age_{target_age}")
        except Exception as e:
            logger.error(f"Age progression failed: {str(e)}")
            raise RuntimeError("Age progression processing failed") from e

    def download_image(self, url: str) -> bytes:
        """Reuse URL parsing logic from PostService"""
        bucket = storage.bucket()
        blob_name = None

        p = urlparse(url)
        if "/o/" in p.path:
            blob_name = unquote(p.path.split("/o/")[1])
        else:
            path = p.path.lstrip("/")
            if path.startswith(bucket.name + "/"):
                blob_name = path[len(bucket.name) + 1:]

        if blob_name:
            blob = bucket.blob(blob_name)
            return blob.download_as_bytes()

        # Fallback to HTTP download
        response = requests.get(url)
        response.raise_for_status()
        return response.content

    def resize_image(self, image_bytes: bytes, size: tuple) -> bytes:
        """Resize image while maintaining aspect ratio"""
        img = Image.open(BytesIO(image_bytes)).convert('RGB')
        img.thumbnail(size, Image.Resampling.LANCZOS)

        buf = BytesIO()
        img.save(buf, format='JPEG')
        return buf.getvalue()

    def upload_result(self, image_bytes: bytes, folder: str, subfolder: str) -> str:
        """Upload image using Firebase Storage"""
        bucket = storage.bucket()
        filename = f"{folder}/{subfolder}/{uuid.uuid4()}.jpg"
        blob = bucket.blob(filename)

        blob.upload_from_string(
            image_bytes,
            content_type='image/jpeg'
        )
        blob.make_public()
        return blob.public_url

    def _call_colab_service(self, image_bytes: bytes, target_age: int) -> bytes:
        """Call the Colab-hosted age progression service"""
        # Prepare request
        files = {"image": ("input.jpg", image_bytes, "image/jpeg")}
        data = {"target_age": target_age}

        # Send request
        response = requests.post(
            f"{self.colab_service_url}/transform",
            files=files,
            data=data,
            timeout=30
        )
        response.raise_for_status()

        return response.content