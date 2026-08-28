#!/usr/bin/env python3
"""
Utility script to exercise fraud detection paths with canned scenarios.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.utils.db_ops import get_connection
from app.utils.fraud_predictor import ml_model_predict_fraud
from app.utils.fraud_rules import rule_based_fraud_check


def _fetch_reference_user():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, name, age, gender, address, aadhaar,
               ration_id, income_level, dependents, phone, role, created_at
        FROM users
        ORDER BY id ASC
        LIMIT 1
        """
    )
    row = cur.fetchone()
    conn.close()
    return row


def _print_block(title: str, data: dict):
    print(title)
    print(json.dumps(data, indent=2))
    print("-" * 60)


def main():
    user = _fetch_reference_user()
    if not user:
        raise SystemExit("No users found in database. Please register a user first.")

    scenarios = {
        "genuine_low_claim": {
            "rice": 2,
            "wheat": 2,
            "sugar": 1,
            "kerosene": 0,
            "salt": 0.2,
            "soyabeanoil": 0.1,
            "palmoil": 0.0,
            "masoor": 0.5,
            "moong": 0.5,
            "chana": 0.5,
        },
        "fraudulent_high_claim": {
            "rice": 30,
            "wheat": 25,
            "sugar": 15,
            "kerosene": 10,
            "salt": 5,
            "soyabeanoil": 6,
            "palmoil": 6,
            "masoor": 7,
            "moong": 8,
            "chana": 7,
        },
    }

    for label, commodities in scenarios.items():
        ml_flag, ml_score = ml_model_predict_fraud(user, commodities)
        alerts, severity = rule_based_fraud_check(user, commodities, shopkeeper_id=user[0])
        _print_block(
            f"Scenario: {label}",
            {
                "ml_flag": ml_flag,
                "ml_score": round(float(ml_score), 4),
                "rule_severity": severity,
                "rule_alerts": alerts or [],
            },
        )


if __name__ == "__main__":
    main()

