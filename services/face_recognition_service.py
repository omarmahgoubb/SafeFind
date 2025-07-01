from scipy.spatial.distance import cosine
from AiModels.face_recognition.align import align_face
from AiModels.face_recognition.facenet import get_embedding

class FaceRecognitionService:
    THRESHOLD = 0.40        # FaceNet typical cosine cutoff

    def compare_faces(self, img_a_bytes: bytes, img_b_bytes: bytes) -> float:
        crop_a = align_face(img_a_bytes)
        crop_b = align_face(img_b_bytes)
        if crop_a is None or crop_b is None:
            raise ValueError("Face not detected in one of the images.")
        emb_a = get_embedding(crop_a)
        emb_b = get_embedding(crop_b)
        return float(cosine(emb_a, emb_b))   # 0 = identical, 1 = orthogonal
