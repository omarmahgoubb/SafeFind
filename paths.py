import os

# Firebase Admin SDK JSON file path
FIREBASE_ADMIN_SDK_PATH = os.path.join(os.path.dirname(__file__), "safefind-e93cf-firebase-adminsdk-fbsvc-9cc89ef13b.json")

# Siamese model H5 file path
SIAMESE_MODEL_PATH = os.path.join(os.path.dirname(__file__), "AiModels", "face_recognition", "siamese_model.h5")

# Siamese network Python file path
SIAMESE_NETWORK_PATH = os.path.join(os.path.dirname(__file__), "AiModels", "face_recognition", "siamese_network.py")

# Train model Python file path
TRAIN_MODEL_PATH = os.path.join(os.path.dirname(__file__), "AiModels", "face_recognition", "train_model.py")

# Train shell script path
TRAIN_SH_PATH = os.path.join(os.path.dirname(__file__), "AiModels", "face_recognition", "train.sh")

# Test model Python file path
TEST_MODEL_PATH = os.path.join(os.path.dirname(__file__), "AiModels", "face_recognition", "test_model.py")

# Test shell script path
TEST_SH_PATH = os.path.join(os.path.dirname(__file__), "AiModels", "face_recognition", "test.sh")

# Prepare LFW data Python file path
PREPARE_LFW_DATA_PATH = os.path.join(os.path.dirname(__file__), "AiModels", "face_recognition", "prepare_lfw_data.py")

# Firebase Storage Bucket URL Prefix
FIREBASE_STORAGE_BUCKET_URL_PREFIX = "https://storage.googleapis.com/safefind-e93cf.appspot.com"


