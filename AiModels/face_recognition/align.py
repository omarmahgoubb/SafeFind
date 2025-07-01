# AiModels/face_recognition/align.py
import numpy as np, cv2
from mtcnn.mtcnn import MTCNN

_detector = MTCNN()

def align_face(raw_bytes: bytes) -> np.ndarray | None:
    img_bgr = cv2.imdecode(np.frombuffer(raw_bytes, np.uint8), cv2.IMREAD_COLOR)
    if img_bgr is None:
        return None
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    dets = _detector.detect_faces(img_rgb)
    if not dets:
        return None
    x, y, w, h = max(dets, key=lambda d: d['box'][2]*d['box'][3])['box']
    x, y = max(0, x), max(0, y)
    return img_rgb[y:y+h, x:x+w].astype("float32")
