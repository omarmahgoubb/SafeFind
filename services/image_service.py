# services/image_service.py
import cv2
import numpy as np
import imghdr

#nzbt el preprocessing bta3 el sora
# ── tunables ─────────────────────────────────────────────────────────
ALLOWED_TYPES   = {"jpeg", "png"}
MIN_SIDE        = 320       # px   – reject tiny pictures
BLUR_VAR_THRES  = 80        # Laplacian variance threshold
RESIZE_TO       = 1080      # px   – long side after resize
JPEG_QUALITY    = 90        # %

# ── internal helpers ─────────────────────────────────────────────────
def _reject_small_or_blur(bgr: np.ndarray) -> None:
    h, w = bgr.shape[:2]
    if min(h, w) < MIN_SIDE:
        raise ValueError("Image too small")
    lap_var = cv2.Laplacian(
        cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY), cv2.CV_64F
    ).var()
    if lap_var < BLUR_VAR_THRES:
        raise ValueError("Image too blurry")

# ── public API ───────────────────────────────────────────────────────
def preprocess(image_bytes: bytes) -> tuple[bytes, str]:
    """
    Validates & normalises an uploaded image.
    Returns (JPEG bytes, 'jpeg').
    """
    img_type = imghdr.what(None, image_bytes)
    if img_type not in ALLOWED_TYPES:
        raise ValueError("Only JPEG and PNG images are allowed")

    bgr = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
    if bgr is None:
        raise ValueError("Corrupt image file")

    _reject_small_or_blur(bgr)

    # central square crop then resize (if larger than RESIZE_TO)
    h, w = bgr.shape[:2]
    side = min(h, w)
    y0   = (h - side) // 2
    x0   = (w - side) // 2
    crop = bgr[y0 : y0 + side, x0 : x0 + side]

    if side > RESIZE_TO:
        crop = cv2.resize(crop, (RESIZE_TO, RESIZE_TO))

    ok, clean = cv2.imencode(
        ".jpg", crop, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY]
    )
    if not ok:
        raise RuntimeError("Failed to encode image")

    return clean.tobytes(), "jpeg"
