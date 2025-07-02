from PIL import Image
from io import BytesIO


class ImageUtils:
    @staticmethod
    def bytes_to_pil(image_bytes: bytes) -> Image.Image:
        return Image.open(BytesIO(image_bytes)).convert('RGB')

    @staticmethod
    def pil_to_bytes(pil_image: Image.Image, format: str = 'JPEG') -> bytes:
        buf = BytesIO()
        pil_image.save(buf, format=format)
        return buf.getvalue()

    @staticmethod
    def resize_image(image_bytes: bytes, size: tuple) -> bytes:
        pil_image = ImageUtils.bytes_to_pil(image_bytes)
        pil_image.thumbnail(size, Image.Resampling.LANCZOS)
        return ImageUtils.pil_to_bytes(pil_image)