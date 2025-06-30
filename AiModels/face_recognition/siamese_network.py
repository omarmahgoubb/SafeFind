"""
Siamese-network definition and custom helpers
---------------------------------------------

• build_base_network(...)      → shared convolutional tower
• build_siamese_model(...)     → full model (two inputs → distance)
• euclidean_distance(...)      → Lambda for distance
• eucl_dist_output_shape(...)  → tells Keras the Lambda’s output shape
• contrastive_loss(...)        → training loss

All helper functions are registered with @register_keras_serializable()
so the model can be saved / loaded without custom_objects.
"""

import tensorflow as tf
from keras.layers import (
    Activation,
    Conv2D,
    MaxPooling2D,
    Dropout,
    Flatten,
    Dense,
    Input,
    Lambda,
)
from keras.models import Sequential, Model
from keras.saving import register_keras_serializable

# ───────────────── shared tower ──────────────────────────────
def build_base_network(input_shape):
    """
    Returns a small CNN that outputs a 50-D feature vector.
    The network expects input in channels-first format: (C, H, W).
    """
    seq = Sequential(name="base_cnn")

    nb_filter   = [6, 12]
    kernel_size = 3

    # conv-block 1
    seq.add(
        Conv2D(
            nb_filter[0],
            (kernel_size, kernel_size),
            input_shape=input_shape,
            padding="valid",
            data_format="channels_first",
        )
    )
    seq.add(Activation("relu"))
    seq.add(MaxPooling2D((2, 2), data_format="channels_first"))
    seq.add(Dropout(0.25))

    # conv-block 2
    seq.add(
        Conv2D(
            nb_filter[1],
            (kernel_size, kernel_size),
            padding="valid",
            data_format="channels_first",
        )
    )
    seq.add(Activation("relu"))
    seq.add(MaxPooling2D((2, 2), data_format="channels_first"))
    seq.add(Dropout(0.25))

    # dense head
    seq.add(Flatten())
    seq.add(Dense(128, activation="relu"))
    seq.add(Dropout(0.1))
    seq.add(Dense(50, activation="relu"))

    return seq


# ───────────────── helpers for Lambda layer ──────────────────
@register_keras_serializable()
def euclidean_distance(vects):
    x, y = vects
    return tf.math.sqrt(tf.math.reduce_sum(tf.math.square(x - y), axis=1, keepdims=True))


@register_keras_serializable()
def eucl_dist_output_shape(shapes):
    shape1, _ = shapes
    return (shape1[0], 1)


# ───────────────── loss function ─────────────────────────────
@register_keras_serializable()
def contrastive_loss(y_true, y_pred):
    margin = 1.0
    return tf.math.reduce_mean(
        y_true * tf.math.square(y_pred)
        + (1 - y_true) * tf.math.square(tf.math.maximum(margin - y_pred, 0.0))
    )


# ───────────────── assemble full Siamese model ───────────────
def build_siamese_model(input_shape):
    """
    Assemble the Siamese network with shared weights and
    a Lambda distance layer.
    """
    input_a = Input(shape=input_shape, name="input_a")
    input_b = Input(shape=input_shape, name="input_b")

    base_network = build_base_network(input_shape)

    feat_a = base_network(input_a)
    feat_b = base_network(input_b)

    distance = Lambda(
        euclidean_distance, output_shape=eucl_dist_output_shape, name="distance"
    )([feat_a, feat_b])

    return Model([input_a, input_b], distance, name="siamese_network")


# ───────────────── explicit exports ──────────────────────────
__all__ = [
    "build_base_network",
    "build_siamese_model",
    "euclidean_distance",
    "eucl_dist_output_shape",
    "contrastive_loss",
]
