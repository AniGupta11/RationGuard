#!/usr/bin/env python3
"""
Preprocess clean dataset → encoded, scaled, np arrays.
"""

import pandas as pd
import numpy as np
import os
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder, StandardScaler
import joblib

CLEAN_PATH = "data/processed/rationguard_dataset_clean.csv"
OUT_DIR = "data/processed"
os.makedirs(OUT_DIR, exist_ok=True)

def main():

    df = pd.read_csv(CLEAN_PATH)

    numeric_cols = [
        "Age","Num_Dependents","Total_Entitlement","Total_Claimed",
        "Claimed_vs_Entitled_Percent"
    ]

    for item in ["Wheat","Rice","Kerosene","Sugar","Salt","SoyabeanOil","PalmOil","Masoor","Moong","Chana"]:
        if f"{item}_Entitled" in df.columns:
            numeric_cols.append(f"{item}_Entitled")
        if f"{item}_Claimed" in df.columns:
            numeric_cols.append(f"{item}_Claimed")

    X_num = df[numeric_cols].fillna(0).astype(float)

    cat_cols = ["Gender","Income_Level","Subsidy_Availed"]

    # Encoder
    ohe = OneHotEncoder(sparse=False, handle_unknown="ignore")
    X_cat = ohe.fit_transform(df[cat_cols])

    joblib.dump({"ohe": ohe, "cat_cols": cat_cols},
                "data/processed/encoder.pkl")

    # Fraud flag columns
    flag_cols = [
        "Duplicate_Aadhaar_Flag","duplicate_rationID_flag","Duplicate_Mobile_Flag",
        "Income_Susbidy_Mismatch","Over_Claim_Flag","Dep_Fraud","Age_Fraud"
    ]

    X_flags = df[flag_cols].astype(int).values

    X_raw = np.hstack([X_num.values, X_cat, X_flags])

    # Scaling
    scaler = StandardScaler()
    X_num_scaled = scaler.fit_transform(X_num.values)

    joblib.dump(scaler, "data/processed/scaler.pkl")

    X = np.hstack([X_num_scaled, X_cat, X_flags])
    y = df["Fraud_Label"].astype(int).values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    np.save("data/processed/X_train.npy", X_train)
    np.save("data/processed/X_test.npy", X_test)
    np.save("data/processed/y_train.npy", y_train)
    np.save("data/processed/y_test.npy", y_test)

    print("PROCESSING DONE → scaler.pkl, encoder.pkl, numpy arrays saved.")

if __name__ == "__main__":
    main()
