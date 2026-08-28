#!/usr/bin/env python3
"""
Clean raw dataset & compute fraud features.
"""

import pandas as pd
import numpy as np
import os

RAW_PATH = "data/raw/rationguard_dataset.csv"
CLEAN_PATH = "data/processed/rationguard_dataset_clean.csv"

def safe_float(x):
    try:
        return float(x)
    except:
        return np.nan

def main():

    if not os.path.exists(RAW_PATH):
        raise FileNotFoundError(f"RAW dataset not found at {RAW_PATH}")

    df = pd.read_csv(RAW_PATH)

    df["Age"] = pd.to_numeric(df["Age"], errors="coerce").fillna(0).astype(int)
    df["Num_Dependents"] = pd.to_numeric(df["Num_Dependents"], errors="coerce").fillna(0).astype(int)

    ent_cols = [c for c in df.columns if c.endswith("_Entitled")]
    clm_cols = [c for c in df.columns if c.endswith("_Claimed")]

    if ent_cols:
        df["Total_Entitlement"] = df[ent_cols].apply(lambda r: pd.to_numeric(r, errors="coerce").sum(), axis=1)
    if clm_cols:
        df["Total_Claimed"] = df[clm_cols].apply(lambda r: pd.to_numeric(r, errors="coerce").sum(), axis=1)

    df["Total_Entitlement"] = df["Total_Entitlement"].fillna(0)
    df["Total_Claimed"] = df["Total_Claimed"].fillna(0)

    df["Claimed_vs_Entitled_Percent"] = df.apply(
        lambda r: (r["Total_Claimed"] / r["Total_Entitlement"]) * 100 if r["Total_Entitlement"] > 0 else 0,
        axis=1
    ).round(2)

    df["Duplicate_Aadhaar_Flag"] = df["Aadhaar_ID"].duplicated(keep=False).astype(int)
    df["duplicate_rationID_flag"] = df["Ration_ID"].duplicated(keep=False).astype(int)
    df["Duplicate_Mobile_Flag"] = df["Phone_No"].duplicated(keep=False).astype(int)

    df["Income_Susbidy_Mismatch"] = (
        (df["Income_Level"] == "High") & (df["Subsidy_Availed"] == "Yes")
    ).astype(int)

    df["Over_Claim_Flag"] = (df["Total_Claimed"] > df["Total_Entitlement"]).astype(int)
    df["Dep_Fraud"] = (df["Num_Dependents"] > 6).astype(int)
    df["Age_Fraud"] = (df["Age"] < 6).astype(int)

    df["Fraud_Label"] = (
        df["Duplicate_Aadhaar_Flag"] |
        df["duplicate_rationID_flag"] |
        df["Duplicate_Mobile_Flag"] |
        df["Income_Susbidy_Mismatch"] |
        df["Over_Claim_Flag"] |
        df["Dep_Fraud"] |
        df["Age_Fraud"]
    ).astype(int)

    def remarks(row):
        r = []
        if row["Duplicate_Aadhaar_Flag"]: r.append("Duplicate Aadhaar detected")
        if row["duplicate_rationID_flag"]: r.append("Ration ID duplicated across households")
        if row["Duplicate_Mobile_Flag"]: r.append("Shared mobile number across multiple households")
        if row["Income_Susbidy_Mismatch"]: r.append("High-income household availing subsidy")
        if row["Over_Claim_Flag"]: r.append("Overclaim detected beyond entitled quota")
        if row["Dep_Fraud"]: r.append("Dependents exceed legal limit")
        if row["Age_Fraud"]: r.append("Age below legal limit")
        return "; ".join(r)

    df["Remarks"] = df.apply(remarks, axis=1)

    df.to_csv(CLEAN_PATH, index=False)
    print("CLEAN DATASET SAVED TO:", CLEAN_PATH)

if __name__ == "__main__":
    main()
