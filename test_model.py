import os
import numpy as np
import cv2
from services.face_recognition_service import FaceRecognitionService
from keras.models import load_model
from services.face_recognition_service import contrastive_loss, euclidean_distance, eucl_dist_output_shape

PREPARED_DATA_DIR = r"C:\Users\omara\Desktop\GradProject\data\lfw_prepared"
PAIRS_FILE = os.path.join(PREPARED_DATA_DIR, "lfw_pairs.txt")
MODEL_LOAD_PATH = r"C:\Users\omara\Desktop\GradProject\siamese_model.h5"


# Image dimensions for the model
IMG_HEIGHT, IMG_WIDTH = 100, 100
CHANNELS = 1 # Grayscale
INPUT_SHAPE = (CHANNELS, IMG_HEIGHT, IMG_WIDTH)

def load_and_preprocess_image(image_path):
    img = cv2.imread(image_path)
    if img is None:
        print(f"Warning: Could not load image {image_path}")
        return None
    gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    resized_img = cv2.resize(gray_img, (IMG_WIDTH, IMG_HEIGHT))
    processed_img = np.expand_dims(resized_img, axis=0) # Add channel dimension
    processed_img = processed_img / 255.0 # Normalize
    return processed_img

def load_pairs_from_file(pairs_file):
    pairs = []
    with open(pairs_file, "r") as f:
        for line in f:
            img1_path, img2_path, label = line.strip().split(",")
            pairs.append(((img1_path, img2_path), int(label)))
    return pairs

if __name__ == "__main__":
    print("Loading model...")
    try:
        # Custom objects are needed to load a model with custom loss functions or layers
        model = load_model(MODEL_LOAD_PATH, custom_objects={
            'contrastive_loss': contrastive_loss,
            'euclidean_distance': euclidean_distance,
            'eucl_dist_output_shape': eucl_dist_output_shape
        })
        print("Model loaded successfully.")
    except Exception as e:
        print(f"Error loading model: {e}")
        print(f"Please ensure a trained model exists at {MODEL_LOAD_PATH}")
        exit()

    print("Loading test data...")
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

    # For testing, we can use a subset of the valid pairs or all of them
    # Let's use a small subset for a quick test
    test_pairs = valid_pairs[::100] # Take every 100th pair for a quick test
    print(f"Testing with {len(test_pairs)} pairs.")

    correct_predictions = 0
    total_predictions = 0
    
    for (img1_data, img2_data), true_label in test_pairs:
        # Predict the distance
        distance = model.predict([np.array([img1_data]), np.array([img2_data])])[0][0]
        
        # Determine prediction based on a threshold (e.g., 0.5)
        # If distance < threshold, it's a match (similar), so predicted_label = 1
        # If distance >= threshold, it's not a match (dissimilar), so predicted_label = 0
        predicted_label = 1 if distance < 0.5 else 0 # This threshold may need tuning

        print(f"Distance: {distance:.4f}, True Label: {true_label}, Predicted Label: {predicted_label}")

        if predicted_label == true_label:
            correct_predictions += 1
        total_predictions += 1

    if total_predictions > 0:
        accuracy = correct_predictions / total_predictions
        print(f"\nTest complete. Accuracy: {accuracy:.2f} ({correct_predictions}/{total_predictions})")
    else:
        print("No predictions were made.")


