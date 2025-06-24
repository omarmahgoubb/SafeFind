import os
import numpy as np
import cv2
from sklearn.model_selection import train_test_split
from services.face_recognition_service import FaceRecognitionService
from keras.callbacks import ModelCheckpoint

# Define paths
PREPARED_DATA_DIR = r"C:\Users\omara\Desktop\GradProject\data\lfw_prepared"
PAIRS_FILE = os.path.join(PREPARED_DATA_DIR, "lfw_pairs.txt")
MODEL_SAVE_PATH = r"C:\Users\omara\Desktop\GradProject\siamese_model.h5"

# Image dimensions for the model
IMG_HEIGHT, IMG_WIDTH = 100, 100
CHANNELS = 1  # Grayscale
INPUT_SHAPE = (CHANNELS, IMG_HEIGHT, IMG_WIDTH)

def load_and_preprocess_image(image_path):
    img = cv2.imread(image_path)
    if img is None:
        print(f"Warning: Could not load image {image_path}")
        return None
    gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    resized_img = cv2.resize(gray_img, (IMG_WIDTH, IMG_HEIGHT))
    processed_img = np.expand_dims(resized_img, axis=0)  # Add channel dimension
    processed_img = processed_img / 255.0  # Normalize
    return processed_img

def load_pairs_from_file(pairs_file):
    pairs = []
    with open(pairs_file, "r") as f:
        for line in f:
            img1_path, img2_path, label = line.strip().split(",")
            pairs.append(((img1_path, img2_path), int(label)))
    return pairs

if __name__ == "__main__":
    print("Loading and preparing data for training...")
    all_pairs_data = load_pairs_from_file(PAIRS_FILE)

    # Filter out any pairs where images could not be loaded
    valid_pairs = []
    for (img1_path, img2_path), label in all_pairs_data:
        img1 = load_and_preprocess_image(img1_path)
        img2 = load_and_preprocess_image(img2_path)
        if img1 is not None and img2 is not None:
            valid_pairs.append(((img1, img2), label))
    
    if not valid_pairs:
        print("No valid pairs found after image loading and preprocessing. Exiting.")
        exit()

    # Split data into training and validation sets (80% train, 20% val)
    X = [pair[0] for pair in valid_pairs]
    y = [pair[1] for pair in valid_pairs]

    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)

    # Convert lists of images to numpy arrays for Keras
    X_train_img1 = np.array([x[0] for x in X_train])
    X_train_img2 = np.array([x[1] for x in X_train])
    y_train = np.array(y_train)

    X_val_img1 = np.array([x[0] for x in X_val])
    X_val_img2 = np.array([x[1] for x in X_val])
    y_val = np.array(y_val)

    print(f"Training with {len(X_train)} pairs, validating with {len(X_val)} pairs.")

    # Initialize the Siamese network model
    face_recognition_service = FaceRecognitionService(input_shape=INPUT_SHAPE)
    model = face_recognition_service.get_model()

    # Define callbacks for saving the best model
    checkpoint = ModelCheckpoint(MODEL_SAVE_PATH, monitor='val_loss', verbose=1, save_best_only=True, mode='min')

    print("Starting model training...")
    # Train the model
    model.fit(
        [X_train_img1, X_train_img2],
        y_train,
        batch_size=128,
        epochs=10,  # You can adjust the number of epochs
        validation_data=([X_val_img1, X_val_img2], y_val),
        callbacks=[checkpoint]
    )

    print(f"Model training complete. Best model saved to {MODEL_SAVE_PATH}")


