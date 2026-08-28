#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Complete pipeline: Clean dataset, preprocess, and train Dense ANN model.
All outputs saved in the same directory as this script.
Target: ~90% accuracy
"""

import os
import sys
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
import joblib
import warnings
warnings.filterwarnings('ignore')

# Get script directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

print("\n" + "="*70)
print("RationGuard - Complete ML Pipeline (Target: 90% Accuracy)".center(70))
print("="*70 + "\n")

# ============================================================================
# STEP 1: LOAD RAW DATA
# ============================================================================
print("="*70)
print("STEP 1: Loading Raw Dataset")
print("="*70)

raw_data_path = os.path.join(SCRIPT_DIR, "rationguard_dataset.csv")

if not os.path.exists(raw_data_path):
    print(f"Error: Raw dataset not found at {raw_data_path}")
    sys.exit(1)

df_raw = pd.read_csv(raw_data_path)
print(f"[OK] Loaded dataset: {df_raw.shape[0]} records, {df_raw.shape[1]} columns")
print(f"[OK] Fraud distribution:\n{df_raw['Fraud_Label'].value_counts()}\n")

# ============================================================================
# STEP 2: CLEAN DATASET
# ============================================================================
print("="*70)
print("STEP 2: Cleaning Dataset")
print("="*70)

df_clean = df_raw.copy()

# Handle missing values
print("[OK] Handling missing values...")
df_clean = df_clean.fillna(0)

# Remove duplicates
initial_rows = len(df_clean)
df_clean = df_clean.drop_duplicates()
duplicates_removed = initial_rows - len(df_clean)
print(f"[OK] Removed {duplicates_removed} duplicate records")

# Data type conversions and validation
print("[OK] Validating data types...")
numeric_cols = ['Age', 'Num_Dependents', 'Total_Entitlement', 'Total_Claimed', 
                'Claimed_vs_Entitled_Percent']
for col in numeric_cols:
    if col in df_clean.columns:
        df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce').fillna(0)

# Remove rows with invalid ages
print("[OK] Removing invalid age records...")
initial_rows = len(df_clean)
df_clean = df_clean[df_clean['Age'] > 0]
invalid_removed = initial_rows - len(df_clean)
print(f"[OK] Removed {invalid_removed} records with invalid age")

# Ensure all feature columns exist
required_features = [
    'Age', 'Income_Level', 'Subsidy_Availed', 'Num_Dependents',
    'Total_Entitlement', 'Total_Claimed', 'Claimed_vs_Entitled_Percent',
    'Duplicate_Aadhaar_Flag', 'duplicate_rationID_flag', 'Duplicate_Mobile_Flag',
    'Income_Subsidy_Mismatch', 'Over_Claim_Flag', 'Dep_Fraud', 'Age_Fraud',
    'Fraud_Label'
]

missing_features = [f for f in required_features if f not in df_clean.columns]
if missing_features:
    print(f"[WARNING] Missing features will be added: {missing_features}")
    for col in missing_features:
        if col != 'Fraud_Label':
            df_clean[col] = 0

# Ensure fraud label is binary
df_clean['Fraud_Label'] = (df_clean['Fraud_Label'].astype(int) > 0).astype(int)

print(f"[OK] Final cleaned dataset: {df_clean.shape[0]} records, {df_clean.shape[1]} columns")
print(f"[OK] Fraud ratio: {df_clean['Fraud_Label'].sum() / len(df_clean) * 100:.2f}%")

# Save cleaned dataset
cleaned_csv_path = os.path.join(SCRIPT_DIR, "dataset_cleaned.csv")
df_clean.to_csv(cleaned_csv_path, index=False)
print(f"[OK] Cleaned dataset saved: {cleaned_csv_path}\n")

# ============================================================================
# STEP 3: PREPROCESS DATA
# ============================================================================
print("="*70)
print("STEP 3: Preprocessing Data")
print("="*70)

df_processed = df_clean.copy()

# Select features for modeling
feature_columns = [
    'Age', 'Income_Level', 'Subsidy_Availed', 'Num_Dependents',
    'Total_Entitlement', 'Total_Claimed', 'Claimed_vs_Entitled_Percent',
    'Duplicate_Aadhaar_Flag', 'duplicate_rationID_flag', 'Duplicate_Mobile_Flag',
    'Income_Subsidy_Mismatch', 'Over_Claim_Flag', 'Dep_Fraud', 'Age_Fraud'
]

# Encode categorical variables
print("[OK] Encoding categorical features...")
label_encoders = {}

for col in ['Income_Level', 'Subsidy_Availed']:
    if col in df_processed.columns:
        le = LabelEncoder()
        df_processed[col] = le.fit_transform(df_processed[col].astype(str))
        label_encoders[col] = le
        print(f"     - {col}: {list(le.classes_)}")

# Extract features and target
available_features = [f for f in feature_columns if f in df_processed.columns]
X = df_processed[available_features].values
y = df_processed['Fraud_Label'].values

# Handle NaN values
X = np.nan_to_num(X, nan=0.0)

print(f"[OK] Feature matrix shape: {X.shape}")
print(f"[OK] Target shape: {y.shape}")
print(f"[OK] Features used: {available_features}\n")

# ============================================================================
# STEP 4: SPLIT AND SCALE DATA
# ============================================================================
print("="*70)
print("STEP 4: Splitting and Scaling Data")
print("="*70)

# Train-test split with stratification
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# Scale features
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

print(f"[OK] Training set: {X_train_scaled.shape}")
print(f"     Fraud cases: {y_train.sum()} ({y_train.sum()/len(y_train)*100:.2f}%)")
print(f"[OK] Test set: {X_test_scaled.shape}")
print(f"     Fraud cases: {y_test.sum()} ({y_test.sum()/len(y_test)*100:.2f}%)\n")

# Save preprocessed data
np.save(os.path.join(SCRIPT_DIR, "X_train.npy"), X_train_scaled)
np.save(os.path.join(SCRIPT_DIR, "X_test.npy"), X_test_scaled)
np.save(os.path.join(SCRIPT_DIR, "y_train.npy"), y_train)
np.save(os.path.join(SCRIPT_DIR, "y_test.npy"), y_test)

print(f"[OK] Preprocessed data saved:")
print(f"     - {os.path.join(SCRIPT_DIR, 'X_train.npy')}")
print(f"     - {os.path.join(SCRIPT_DIR, 'X_test.npy')}")
print(f"     - {os.path.join(SCRIPT_DIR, 'y_train.npy')}")
print(f"     - {os.path.join(SCRIPT_DIR, 'y_test.npy')}\n")

# ============================================================================
# STEP 5: BUILD AND TRAIN DENSE ANN MODEL
# ============================================================================
print("="*70)
print("STEP 5: Building and Training Dense ANN Model")
print("="*70)

# Using TensorFlow 2.x with Keras API
print("\n[OK] Initializing TensorFlow/Keras for Dense ANN...")

try:
    import os as os_module
    os_module.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
    
    # Clean import
    import tensorflow
    from tensorflow import keras
    from tensorflow.keras import layers, models, callbacks, optimizers  # type: ignore
    from tensorflow.keras.regularizers import l1_l2  # type: ignore
    
    print("[OK] TensorFlow/Keras loaded successfully")
    
    # Build Dense ANN model (Feed-forward Neural Network with Batch Normalization)
    print("\n[OK] Building Dense ANN Architecture (Feed-Forward Network)...")
    print("     (Configured for ~90% accuracy with strong regularization)")
    
    model = models.Sequential(name='fraud_detection_ann')
    
    # Input layer + first hidden layer (40 neurons) 
    model.add(layers.Dense(40, activation='relu', input_shape=(X_train_scaled.shape[1],),
                          kernel_initializer='he_normal', kernel_regularizer=l1_l2(l1=0.006, l2=0.006),
                          name='dense_input'))
    model.add(layers.Dropout(0.45, name='dropout_1'))
    
    # Second hidden layer (20 neurons)
    model.add(layers.Dense(20, activation='relu', kernel_initializer='he_normal', 
                          kernel_regularizer=l1_l2(l1=0.006, l2=0.006), name='dense_2'))
    model.add(layers.Dropout(0.45, name='dropout_2'))
    
    # Output layer
    model.add(layers.Dense(1, activation='sigmoid', name='output'))
    
    # Compile model
    optimizer = optimizers.Adam(learning_rate=0.0008)
    model.compile(
        optimizer=optimizer,
        loss='binary_crossentropy',
        metrics=['accuracy', keras.metrics.AUC(name='auc')]
    )
    
    print("\n[OK] Model Architecture Summary:")
    print("-" * 70)
    model.summary()
    print("-" * 70)
    
    # Define callbacks
    checkpoint_path = os.path.join(SCRIPT_DIR, "fraud_model_best.h5")
    ckpt = callbacks.ModelCheckpoint(
        checkpoint_path,
        monitor='val_auc',
        save_best_only=True,
        mode='max',
        verbose=0
    )
    
    early_stop = callbacks.EarlyStopping(
        monitor='val_auc',
        patience=15,
        restore_best_weights=True,
        verbose=0
    )
    
    # Train model
    print("\n[OK] Training Dense ANN Model (45 epochs with early stopping)...")
    print("-" * 70)
    history = model.fit(
        X_train_scaled, y_train,
        validation_split=0.2,
        epochs=45,
        batch_size=96,
        callbacks=[ckpt, early_stop],
        verbose=1
    )
    print("-" * 70)
    
    # Save final model in H5 format
    final_model_path = os.path.join(SCRIPT_DIR, "fraud_model.h5")
    model.save(final_model_path)
    print(f"\n[OK] Final model saved in H5 format: {final_model_path}")
    print(f"[OK] Best checkpoint saved: {checkpoint_path}")
    
    # ========================================================================
    # STEP 6: EVALUATE MODEL
    # ========================================================================
    print("\n" + "="*70)
    print("STEP 6: Model Evaluation")
    print("="*70)
    
    # Predictions on test set
    y_pred_proba = model.predict(X_test_scaled, verbose=0).ravel()
    y_pred = (y_pred_proba >= 0.5).astype(int)
    
    # Calculate metrics
    auc = roc_auc_score(y_test, y_pred_proba)
    cm = confusion_matrix(y_test, y_pred)
    tn, fp, fn, tp = cm.ravel()
    
    accuracy = (tp + tn) / (tp + tn + fp + fn)
    sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    f1_score = 2 * (precision * sensitivity) / (precision + sensitivity) if (precision + sensitivity) > 0 else 0
    
    print(f"\n[OK] Test Set Performance Metrics:")
    print(f"     - AUC Score: {auc:.4f}")
    print(f"     - Accuracy: {accuracy:.4f}")
    print(f"     - Precision: {precision:.4f}")
    print(f"     - Recall (Sensitivity): {sensitivity:.4f}")
    print(f"     - Specificity: {specificity:.4f}")
    print(f"     - F1-Score: {f1_score:.4f}")
    
    print(f"\n[OK] Confusion Matrix:")
    print(f"                    Predicted")
    print(f"                 Genuine  Fraud")
    print(f"     Actual  Genuine    {tn:5d}  {fp:5d}")
    print(f"             Fraud      {fn:5d}  {tp:5d}")
    
    print(f"\n[OK] Classification Report:")
    print(classification_report(y_test, y_pred, target_names=["Genuine", "Fraud"]))
    
    # Save metadata
    metadata = {
        'feature_names': available_features,
        'label_encoders': label_encoders,
        'scaler_mean': scaler.mean_,
        'scaler_std': scaler.scale_,
        'model_metrics': {
            'auc': float(auc),
            'accuracy': float(accuracy),
            'precision': float(precision),
            'recall': float(sensitivity),
            'f1_score': float(f1_score)
        }
    }
    
    metadata_path = os.path.join(SCRIPT_DIR, "model_metadata.pkl")
    joblib.dump(metadata, metadata_path)
    print(f"[OK] Model metadata saved: {metadata_path}")
    
    # ============================================================================
    # FINAL SUMMARY
    # ============================================================================
    print("\n" + "="*70)
    print("PIPELINE EXECUTION COMPLETED SUCCESSFULLY!".center(70))
    print("="*70)
    
    print(f"\nAll outputs saved in: {SCRIPT_DIR}/")
    
    print(f"\nCleaned Dataset:")
    print(f"  - dataset_cleaned.csv ({df_clean.shape[0]} records, {df_clean.shape[1]} columns)")
    
    print(f"\nPreprocessed Data Arrays:")
    print(f"  - X_train.npy ({X_train_scaled.shape})")
    print(f"  - X_test.npy ({X_test_scaled.shape})")
    print(f"  - y_train.npy ({y_train.shape})")
    print(f"  - y_test.npy ({y_test.shape})")
    
    print(f"\nDense ANN Models (H5 Format):")
    print(f"  - fraud_model.h5 (Final Model)")
    print(f"  - fraud_model_best.h5 (Best Checkpoint)")
    print(f"  - model_metadata.pkl (Feature & Metrics)")
    
    print(f"\nFinal Model Performance:")
    print(f"  - AUC: {auc:.4f}")
    print(f"  - Accuracy: {accuracy:.4f}")
    print(f"  - Precision: {precision:.4f}")
    print(f"  - Recall: {sensitivity:.4f}")
    print(f"  - F1-Score: {f1_score:.4f}")
    
    print("\n" + "="*70 + "\n")

except Exception as e:
    print(f"\nERROR during model training: {e}")
    import traceback
    print("\nFull Traceback:")
    traceback.print_exc()
    sys.exit(1)
