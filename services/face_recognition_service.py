import cv2
import numpy as np
import tensorflow as tf
from keras.layers import Activation, Dense, Dropout, Conv2D, MaxPooling2D, Flatten
from keras.models import Sequential, Model
from keras.optimizers import RMSprop
from keras.layers import Input, Lambda



def build_base_network(input_shape):
    seq = Sequential()

    nb_filter = [6, 12]
    kernel_size = 3

    #convolutional layer 1
    seq.add(Conv2D(nb_filter[0],
                   (kernel_size, kernel_size),
                   input_shape=input_shape,
                   padding='valid',
                   data_format="channels_first"))
    seq.add(Activation("relu"))
    seq.add(MaxPooling2D(pool_size=(2, 2), data_format="channels_first"))
    seq.add(Dropout(.25))

    #convolutional layer 2
    seq.add(Conv2D(nb_filter[1],
                   (kernel_size, kernel_size),
                   input_shape=input_shape,
                   padding='valid',
                   data_format="channels_first"))
    seq.add(Activation("relu"))
    seq.add(MaxPooling2D(pool_size=(2, 2), data_format="channels_first"))
    seq.add(Dropout(.25))

    #flatten
    seq.add(Flatten())
    seq.add(Dense(128, activation='relu'))
    seq.add(Dropout(0.1))
    seq.add(Dense(50, activation='relu'))

    return seq

def euclidean_distance(vectors):
    x, y = vectors
    return tf.math.sqrt(tf.math.reduce_sum(tf.math.square(x - y), axis=1, keepdims=True))

def euclidean_dist_output_shape(shapes):
    shape1, shape2 = shapes
    return shape1[0], 1

def contrastive_loss(y_true, y_pred):
    margin = 1
    return tf.math.reduce_mean(
        y_true * tf.math.square(y_pred) +
        (1 - y_true) * tf.math.square(tf.math.maximum(margin - y_pred, 0))
    )

def build_siamese_model(input_shape):
    # Define the tensors for the two input images
    input_a = Input(shape=input_shape)
    input_b = Input(shape=input_shape)

    # Neural network to learn image features
    base_network = build_base_network(input_shape)

    # Process the two inputs
    processed_a = base_network(input_a)
    processed_b = base_network(input_b)

    # Keras Lambda layer to calculate the Euclidean distance between the two vectors
    distance = Lambda(euclidean_distance, output_shape=euclidean_dist_output_shape)([processed_a, processed_b])

    # Define the model
    model = Model(inputs=[input_a, input_b], outputs=distance)

    # Return the model
    return model

class FaceRecognitionService:
    def __init__(self, input_shape=(1, 100, 100)): # Assuming 1 channel (grayscale), 100x100 images
        self.model = build_siamese_model(input_shape)
        self.model.compile(loss=contrastive_loss, optimizer=RMSprop())

    def get_model(self):
        return self.model

    @staticmethod
    def preprocess_image_for_model(image_bytes):
        # This is a placeholder. You will need to implement proper image preprocessing
        # to match the input requirements of your Siamese network.
        # This might involve resizing, grayscale conversion, normalization, etc.
        # For now, I'm just returning a dummy array.
        # You should integrate with the existing image_service.py for actual preprocessing.
        
        # Example: Convert to grayscale and resize to 100x100
        par = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(par, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Could not decode image bytes.")
        
        gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        resized_img = cv2.resize(gray_img, (100, 100))
        
        # Add channel dimension and batch dimension
        processed_img = np.expand_dims(resized_img, axis=0) # Add channel dimension (1, 100, 100)
        processed_img = np.expand_dims(processed_img, axis=0) # Add batch dimension (1, 1, 100, 100)
        
        # Normalize pixel values to be between 0 and 1
        processed_img = processed_img / 255.0
        
        return processed_img

    def compare_faces(self, image1_bytes, image2_bytes):
        # Preprocess images for the model
        img1_processed = self.preprocess_image_for_model(image1_bytes)
        img2_processed = self.preprocess_image_for_model(image2_bytes)

        # Predict the distance between the two images
        distance = self.model.predict([img1_processed, img2_processed])[0][0]
        return distance






