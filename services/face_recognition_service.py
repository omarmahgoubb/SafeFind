# services/face_recognition_service.py
import cv2
import numpy as np
import tensorflow as tf
from keras.models import load_model
from keras.optimizers import RMSprop
from paths import SIAMESE_MODEL_PATH
from AiModels.face_recognition.siamese_network import (             # your builder & helpers
    build_siamese_model,
    euclidean_distance,
    eucl_dist_output_shape,
    contrastive_loss,
)

# ───────────── Helper for data prep ────────────────────────────
def _preprocess(image_bytes: bytes, size=(100, 100)) -> np.ndarray:
    """Return a (1, 1, H, W) float32 image tensor in range 0‒1."""
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image bytes")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    resized = cv2.resize(gray, size)
    tensor = resized.astype("float32") / 255.0          # normalise
    tensor = np.expand_dims(tensor, axis=(0, 1))        # BCHW
    return tensor


# ───────────── Main service class ──────────────────────────────
class FaceRecognitionService:
    """
    If from_scratch=False (default): load the saved Siamese .h5 model.
    If from_scratch=True : build a fresh model for training scripts.
    """

    def __init__(
        self,
        input_shape=(1, 100, 100),
        model_path: str = SIAMESE_MODEL_PATH,
        from_scratch: bool = False,
    ):
        if from_scratch:
            # Training-time path: build & compile a new network
            self.model = build_siamese_model(input_shape)
            self.model.compile(loss=contrastive_loss, optimizer=RMSprop())
        else:
            # Inference path: load the existing .h5
            self.model = load_model(
                model_path,
                custom_objects={
                    "euclidean_distance": euclidean_distance,
                    "eucl_dist_output_shape": eucl_dist_output_shape,
                    "contrastive_loss": contrastive_loss,
                },
            )

    # -----------------------------------------------------------------
    def get_model(self):
        return self.model

    # -----------------------------------------------------------------
    def compare_faces(self, image1_bytes: bytes, image2_bytes: bytes) -> float:
        """
        Returns Euclidean distance (lower = more similar).
        Raises ValueError if either image cannot be decoded.
        """
        img1 = _preprocess(image1_bytes)
        img2 = _preprocess(image2_bytes)
        dist = self.model.predict([img1, img2], verbose=0)[0][0]
        return float(dist)


__all__ = [
    "FaceRecognitionService",
    "euclidean_distance",
    "eucl_dist_output_shape",
    "contrastive_loss",
]