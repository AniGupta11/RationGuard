import os
from datetime import datetime

import joblib
import numpy as np
from keras.models import load_model

from app.utils.db_ops import get_connection
from app.utils.entitlements import (
    calculate_entitlement,
    get_user_entitlements,
)
from app.utils.pricing import calculate_bill

MODEL_PATH = "models/fraud_model.h5"
METADATA_PATH = "models/model_metadata.pkl"
COMMODITY_KEYS = [
    "rice",
    "wheat",
    "sugar",
    "kerosene",
    "salt",
    "soyabeanoil",
    "palmoil",
    "masoor",
    "moong",
    "chana",
]

_model = None
_metadata = None


def _load_metadata():
    global _metadata
    if _metadata is None and os.path.exists(METADATA_PATH):
        _metadata = joblib.load(METADATA_PATH)
    return _metadata


def _load_model():
    global _model
    if _model is None and os.path.exists(MODEL_PATH):
        _model = load_model(MODEL_PATH)
    return _model


def _normalize_income_level(raw_value: str) -> str:
    mapping = {
        "Low Income": "Low",
        "Middle Income": "Medium",
        "High Income": "High",
        "Low": "Low",
        "Medium": "Medium",
        "High": "High",
    }
    return mapping.get((raw_value or "").strip(), "Low")


def _subsidy_amount(income_level: str, total_amount: float) -> float:
    if total_amount <= 0:
        return 0.0
    if income_level == "Low":
        return total_amount
    if income_level == "Medium":
        return total_amount * 0.70
    if income_level == "High":
        return total_amount * 0.40
    return 0.0


def _fetch_duplicate_flags(aadhaar: str, ration_id: str, phone: str):
    if not aadhaar and not ration_id and not phone:
        return {"aadhaar": 0, "ration": 0, "phone": 0}

    conn = get_connection()
    cur = conn.cursor()

    def _count(query, value):
        if not value:
            return 0
        cur.execute(query, (value,))
        row = cur.fetchone()
        return row[0] if row else 0

    aadhaar_count = _count("SELECT COUNT(1) FROM users WHERE aadhaar = ?", aadhaar)
    ration_count = _count("SELECT COUNT(1) FROM users WHERE ration_id = ?", ration_id)
    phone_count = _count("SELECT COUNT(1) FROM users WHERE phone = ?", phone)

    conn.close()
    return {
        "aadhaar": 1 if aadhaar_count > 1 else 0,
        "ration": 1 if ration_count > 1 else 0,
        "phone": 1 if phone_count > 1 else 0,
    }


def _compute_total_entitlement(user_id: int, dependents: int, income_level: str):
    month_year = datetime.now().strftime("%Y-%m")
    entitlements = get_user_entitlements(user_id, month_year)
    if entitlements:
        return float(sum(row[1] for row in entitlements if len(row) > 1))

    per_item_entitlement = calculate_entitlement(dependents, income_level)
    return per_item_entitlement * len(COMMODITY_KEYS)


def _collect_feature_payload(user, commodities_dict):
    user_id = user[0]
    age = int(user[2] or 0)
    dependents = int(user[8] or 0)
    income_level_raw = user[7] or "Low Income"
    income_level_norm = _normalize_income_level(income_level_raw)
    aadhaar = user[5] or ""
    ration_id = user[6] or ""
    phone = user[9] or ""

    total_claimed = float(
        sum(float(commodities_dict.get(key, 0) or 0) for key in COMMODITY_KEYS)
    )
    total_amount = calculate_bill(
        **{key: float(commodities_dict.get(key, 0) or 0) for key in COMMODITY_KEYS}
    )
    total_entitlement = _compute_total_entitlement(
        user_id, dependents, income_level_raw
    )
    claimed_percent = (
        (total_claimed / total_entitlement) * 100 if total_entitlement else 0.0
    )

    duplicates = _fetch_duplicate_flags(aadhaar, ration_id, phone)
    subsidy_amt = _subsidy_amount(income_level_norm, total_amount)
    subsidy_flag = "Yes" if subsidy_amt > 0 else "No"
    income_subsidy_mismatch = 1 if income_level_norm == "High" and subsidy_flag == "Yes" else 0

    over_claim_flag = 0
    if total_entitlement <= 0 and total_claimed > 0:
        over_claim_flag = 1
    elif total_claimed > total_entitlement:
        over_claim_flag = 1

    payload = {
        "Age": float(age),
        "Num_Dependents": float(dependents),
        "Total_Entitlement": float(total_entitlement),
        "Total_Claimed": float(total_claimed),
        "Claimed_vs_Entitled_Percent": float(claimed_percent),
        "Duplicate_Aadhaar_Flag": duplicates["aadhaar"],
        "duplicate_rationID_flag": duplicates["ration"],
        "Duplicate_Mobile_Flag": duplicates["phone"],
        "Income_Subsidy_Mismatch": income_subsidy_mismatch,
        "Over_Claim_Flag": over_claim_flag,
        "Dep_Fraud": 1 if dependents > 6 else 0,
        "Age_Fraud": 1 if age < 6 else 0,
        "Income_Level_label": income_level_norm,
        "Subsidy_Availed_label": subsidy_flag,
    }
    return payload


def _encode_value(encoder, value: str) -> float:
    if encoder is None:
        return 0.0
    classes_attr = getattr(encoder, "classes_", [])
    if len(classes_attr) == 0:
        return 0.0
    classes = set(classes_attr)
    target_value = value
    if value not in classes:
        # Fallback to the first known class to avoid exceptions.
        target_value = classes_attr[0]
    return float(encoder.transform([target_value])[0])


def _build_feature_vector(payload, metadata):
    feature_names = metadata.get("feature_names", [])
    encoders = metadata.get("label_encoders", {})

    values = {}
    values["Income_Level"] = _encode_value(
        encoders.get("Income_Level"), payload["Income_Level_label"]
    )
    values["Subsidy_Availed"] = _encode_value(
        encoders.get("Subsidy_Availed"), payload["Subsidy_Availed_label"]
    )

    for key, value in payload.items():
        if key.endswith("_label"):
            continue
        values[key] = float(value)

    return np.array([values.get(name, 0.0) for name in feature_names], dtype=float)


def _scale_vector(vector, metadata):
    mean = metadata.get("scaler_mean")
    std = metadata.get("scaler_std")
    if mean is None or std is None:
        return vector
    safe_std = np.where(std == 0, 1, std)
    return (vector - mean) / safe_std


def _fallback_flag(payload):
    high_risk_flags = [
        payload.get("Duplicate_Aadhaar_Flag", 0),
        payload.get("duplicate_rationID_flag", 0),
        payload.get("Duplicate_Mobile_Flag", 0),
        payload.get("Over_Claim_Flag", 0),
        payload.get("Dep_Fraud", 0),
        payload.get("Age_Fraud", 0),
    ]
    return any(flag == 1 for flag in high_risk_flags)


def ml_model_predict_fraud(user, commodities_dict):
    """
    Predict fraud using the updated ANN model trained on the generated dataset.
    Falls back to deterministic flags if the model artifacts are unavailable.

    Args:
        user: Tuple from DB (users table)
        commodities_dict: Quantities for all commodities

    Returns:
        tuple(bool, float): (fraud_flag, model_score)
    """
    payload = _collect_feature_payload(user, commodities_dict)
    metadata = _load_metadata()
    model = _load_model()

    if not metadata or not model:
        flag = _fallback_flag(payload)
        return flag, 1.0 if flag else 0.0

    try:
        feature_vector = _build_feature_vector(payload, metadata)
        scaled_vector = _scale_vector(feature_vector, metadata)
        score = float(model.predict(np.array([scaled_vector]), verbose=0)[0][0])
        is_fraud = score >= 0.5
        if not is_fraud and _fallback_flag(payload):
            return True, max(score, 0.5)
        return is_fraud, score
    except Exception:
        flag = _fallback_flag(payload)
        return flag, 1.0 if flag else 0.0
