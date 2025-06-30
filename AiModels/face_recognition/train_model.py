# AiModels/face_recognition/train_model.py
import os
import sys
import pathlib
import cv2
import numpy as np
from sklearn.model_selection import train_test_split
from keras.callbacks import ModelCheckpoint

# ───────── ensure project root on sys.path ─────────
ROOT = pathlib.Path(__file__).resolve().parents[2]  # …/GradProject
sys.path.append(str(ROOT))

from services.face_recognition_service import FaceRecognitionService

# ───────── paths & constants ─────────
PREPARED_DATA_DIR = r"C:\Users\omara\Desktop\GradProject\data\lfw_prepared"
PAIRS_FILE        = os.path.join(PREPARED_DATA_DIR, "lfw_pairs.txt")
MODEL_SAVE_PATH   = r"C:\Users\omara\Desktop\GradProject\siamese_model.h5"

IMG_HEIGHT, IMG_WIDTH = 100, 100
CHANNELS              = 1
INPUT_SHAPE           = (CHANNELS, IMG_HEIGHT, IMG_WIDTH)

# ───────── helpers ─────────
def load_and_preprocess_image(path: str):
    img = cv2.imread(path)
    if img is None:
        print(f"Warning: Could not load image {path}")
        return None
    gray     = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    resized  = cv2.resize(gray, (IMG_WIDTH, IMG_HEIGHT))
    tensor   = resized.astype("float32") / 255.0          # normalise
    tensor   = np.expand_dims(tensor, axis=0)             # (1,H,W)
    return tensor

def load_pairs(txt_file: str):
    pairs = []
    with open(txt_file, "r") as fh:
        for line in fh:
            p1, p2, lbl = line.strip().split(",")
            pairs.append(((p1, p2), int(lbl)))
    return pairs

# ───────── main training routine ─────────
if __name__ == "__main__":
    print("Loading and preparing data for training…")
    raw_pairs = load_pairs(PAIRS_FILE)

    valid_pairs = []
    for (p1, p2), lbl in raw_pairs:
        img1 = load_and_preprocess_image(p1)
        img2 = load_and_preprocess_image(p2)
        if img1 is not None and img2 is not None:
            valid_pairs.append(((img1, img2), lbl))

    if not valid_pairs:
        print("No valid pairs after preprocessing; exiting.")
        sys.exit(1)

    X = [pr[0] for pr in valid_pairs]
    y = [pr[1] for pr in valid_pairs]

    X_tr, X_val, y_tr, y_val = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    X_tr_1 = np.array([x[0] for x in X_tr])
    X_tr_2 = np.array([x[1] for x in X_tr])
    y_tr   = np.array(y_tr)

    X_val_1 = np.array([x[0] for x in X_val])
    X_val_2 = np.array([x[1] for x in X_val])
    y_val   = np.array(y_val)

    print(f"Training with {len(X_tr)} pairs, validating with {len(X_val)} pairs.")

    # ───────── build a fresh model (do NOT load .h5) ─────────
    face_service = FaceRecognitionService(
        input_shape=INPUT_SHAPE,
        from_scratch=True            # build new network
    )
    model = face_service.get_model()

    # ───────── callbacks ─────────
    ckpt = ModelCheckpoint(
        MODEL_SAVE_PATH,
        monitor="val_loss",
        save_best_only=True,
        mode="min",
        verbose=1,
    )

    # ───────── train ─────────
    print("Starting model training…")
    model.fit(
        [X_tr_1, X_tr_2],
        y_tr,
        batch_size=128,
        epochs=10,
        validation_data=([X_val_1, X_val_2], y_val),
        callbacks=[ckpt],
        verbose=1,
    )

    print(f"Training complete; best model saved to {MODEL_SAVE_PATH}")
