import sys
import types
from pathlib import Path

import numpy as np
import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Provide a lightweight keras stub for environments without tensorflow/keras.
if "keras" not in sys.modules:
    keras_stub = types.ModuleType("keras")
    keras_models_stub = types.ModuleType("keras.models")

    def _noop_load_model(*_args, **_kwargs):
        return None

    keras_models_stub.load_model = _noop_load_model
    keras_stub.models = keras_models_stub
    sys.modules["keras"] = keras_stub
    sys.modules["keras.models"] = keras_models_stub

import app.utils.fraud_predictor as fp


class DummyEncoder:
    def __init__(self, classes):
        self.classes_ = classes

    def transform(self, values):
        return [self.classes_.index(values[0])]


class DummyModel:
    def __init__(self, score):
        self._score = score

    def predict(self, arr, verbose=0):
        return np.array([[self._score]])


@pytest.fixture(autouse=True)
def reset_caches():
    fp._metadata = None
    fp._model = None
    yield
    fp._metadata = None
    fp._model = None


def test_ml_model_predict_fraud_ann_path(monkeypatch):
    payload = {
        "Age": 35,
        "Num_Dependents": 2,
        "Total_Entitlement": 40.0,
        "Total_Claimed": 10.0,
        "Claimed_vs_Entitled_Percent": 25.0,
        "Duplicate_Aadhaar_Flag": 0,
        "duplicate_rationID_flag": 0,
        "Duplicate_Mobile_Flag": 0,
        "Income_Subsidy_Mismatch": 0,
        "Over_Claim_Flag": 0,
        "Dep_Fraud": 0,
        "Age_Fraud": 0,
        "Income_Level_label": "Low",
        "Subsidy_Availed_label": "Yes",
    }

    def fake_payload(user, commodities):
        return payload

    feature_names = [
        "Age",
        "Num_Dependents",
        "Total_Entitlement",
        "Total_Claimed",
        "Claimed_vs_Entitled_Percent",
        "Duplicate_Aadhaar_Flag",
        "duplicate_rationID_flag",
        "Duplicate_Mobile_Flag",
        "Income_Subsidy_Mismatch",
        "Over_Claim_Flag",
        "Dep_Fraud",
        "Age_Fraud",
        "Income_Level",
        "Subsidy_Availed",
    ]
    metadata = {
        "feature_names": feature_names,
        "label_encoders": {
            "Income_Level": DummyEncoder(["Low", "Medium", "High"]),
            "Subsidy_Availed": DummyEncoder(["No", "Yes"]),
        },
        "scaler_mean": np.zeros(len(feature_names)),
        "scaler_std": np.ones(len(feature_names)),
    }

    monkeypatch.setattr(fp, "_collect_feature_payload", fake_payload)
    monkeypatch.setattr(fp, "_load_metadata", lambda: metadata)
    monkeypatch.setattr(fp, "_load_model", lambda: DummyModel(0.82))

    user = (1, "Test", 35, "Male", "Addr", "111", "222", "Low Income", 2, "9999999999", "Customer", "2025-01-01")
    commodities = {"rice": 2}

    is_fraud, score = fp.ml_model_predict_fraud(user, commodities)

    assert is_fraud is True
    assert score == pytest.approx(0.82, rel=1e-4)


def test_ml_model_predict_fraud_fallback_flags(monkeypatch):
    payload = {
        "Age": 35,
        "Num_Dependents": 2,
        "Total_Entitlement": 0,
        "Total_Claimed": 0,
        "Claimed_vs_Entitled_Percent": 0,
        "Duplicate_Aadhaar_Flag": 1,
        "duplicate_rationID_flag": 0,
        "Duplicate_Mobile_Flag": 0,
        "Income_Subsidy_Mismatch": 0,
        "Over_Claim_Flag": 0,
        "Dep_Fraud": 0,
        "Age_Fraud": 0,
        "Income_Level_label": "Low",
        "Subsidy_Availed_label": "Yes",
    }

    monkeypatch.setattr(fp, "_collect_feature_payload", lambda *_: payload)
    monkeypatch.setattr(fp, "_load_metadata", lambda: None)
    monkeypatch.setattr(fp, "_load_model", lambda: None)

    user = (1, "Test", 35, "Male", "Addr", "111", "222", "Low Income", 2, "9999999999", "Customer", "2025-01-01")

    is_fraud, score = fp.ml_model_predict_fraud(user, {})
    assert is_fraud is True
    assert score == 1.0


def test_ml_model_predict_fraud_fallback_clean(monkeypatch):
    payload = {
        "Age": 35,
        "Num_Dependents": 2,
        "Total_Entitlement": 0,
        "Total_Claimed": 0,
        "Claimed_vs_Entitled_Percent": 0,
        "Duplicate_Aadhaar_Flag": 0,
        "duplicate_rationID_flag": 0,
        "Duplicate_Mobile_Flag": 0,
        "Income_Subsidy_Mismatch": 0,
        "Over_Claim_Flag": 0,
        "Dep_Fraud": 0,
        "Age_Fraud": 0,
        "Income_Level_label": "Low",
        "Subsidy_Availed_label": "No",
    }

    monkeypatch.setattr(fp, "_collect_feature_payload", lambda *_: payload)
    monkeypatch.setattr(fp, "_load_metadata", lambda: None)
    monkeypatch.setattr(fp, "_load_model", lambda: None)

    user = (1, "Test", 35, "Male", "Addr", "111", "222", "Low Income", 2, "9999999999", "Customer", "2025-01-01")

    is_fraud, score = fp.ml_model_predict_fraud(user, {})
    assert is_fraud is False
    assert score == 0.0

