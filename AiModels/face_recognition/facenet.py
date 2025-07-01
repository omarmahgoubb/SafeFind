# AiModels/face_recognition/facenet.py
from keras_facenet import FaceNet
import numpy as np, time

_embedder = None
def _get_model():
    global _embedder
    if _embedder is None:
        t0 = time.time()
        print("[FaceNet] first boot – downloading weights …")
        _embedder = FaceNet()               # auto-downloads 92 MB .h5 to ~/.keras
        print(f"[FaceNet] ready! ({time.time()-t0:.1f}s)")
    return _embedder

def get_embedding(img_rgb: np.ndarray) -> np.ndarray:
    """
    img_rgb: RGB float32 in [0,255]
    returns : 128-D L2-normalised embedding
    """
    model = _get_model()
    # FaceNet.embeddings returns list[np.ndarray]
    emb = model.embeddings([img_rgb])[0]
    return emb / np.linalg.norm(emb)
