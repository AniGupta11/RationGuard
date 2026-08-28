#!/usr/bin/env python3
"""
Train ANN fraud detection model using processed numpy arrays.
Output: fraud_model.h5
"""

import os
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Dropout, BatchNormalization
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score

DATA_DIR = "/mnt/data/processed"
MODEL_DIR = "/mnt/data/model"
os.makedirs(MODEL_DIR, exist_ok=True)

def main():

    X_train = np.load(os.path.join(DATA_DIR, "X_train.npy"))
    X_test = np.load(os.path.join(DATA_DIR, "X_test.npy"))
    y_train = np.load(os.path.join(DATA_DIR, "y_train.npy"))
    y_test = np.load(os.path.join(DATA_DIR, "y_test.npy"))

    model = Sequential([
        Dense(128, activation="relu", input_shape=(X_train.shape[1],)),
        BatchNormalization(),
        Dropout(0.3),

        Dense(64, activation="relu"),
        BatchNormalization(),
        Dropout(0.2),

        Dense(32, activation="relu"),
        Dense(1, activation="sigmoid")
    ])

    model.compile(optimizer="adam", loss="binary_crossentropy", metrics=["accuracy", "AUC"])

    ckpt = ModelCheckpoint(
        os.path.join(MODEL_DIR, "fraud_model.best.h5"),
        monitor="val_auc",
        save_best_only=True,
        mode="max",
        verbose=1
    )

    es = EarlyStopping(monitor="val_auc", patience=8, restore_best_weights=True)

    history = model.fit(
        X_train, y_train,
        validation_split=0.2,
        epochs=100,
        batch_size=256,
        callbacks=[ckpt, es],
        verbose=2
    )

    model.save(os.path.join(MODEL_DIR, "fraud_model.h5"))

    preds = model.predict(X_test).ravel()
    y_pred = (preds >= 0.5).astype(int)

    print("AUC:", roc_auc_score(y_test, preds))
    print("Confusion Matrix:\n", confusion_matrix(y_test, y_pred))
    print("Report:\n", classification_report(y_test, y_pred))

if __name__ == "__main__":
    main()
