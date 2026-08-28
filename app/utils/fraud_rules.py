"""
Phase-8 D: Rule-based Allocation and Fraud Limits
Fraud Types:
1. Entitlement violation: Requested > allowed limit
2. Repeated abnormal visits: >2 transactions/week
3. High-income loophole: High-income claiming full subsidy
4. Shopkeeper collusion: Same shop → repeated flags
"""
from app.utils.pricing import COMMODITY_LIMITS
from app.utils.db_ops import get_connection
from app.utils.entitlements import get_user_entitlements, get_entitlement_percent
from datetime import datetime, timedelta


def rule_based_fraud_check(user, commodities_dict, shopkeeper_id=None):
    """
    Phase-8 D: Enhanced rule-based fraud check with severity levels
    Returns: (alerts_list, severity_level)
    Severity: "High", "Medium", "Low"
    """
    alerts = []
    severity = "Low"  # Default severity
    
    user_id = user[0]
    age = user[2]  # DB column mapping
    aadhaar = user[5]
    income_level = user[7]  # income_level
    dependents = user[8]

    # Rule 1: Age-based validation
    if age < 18:
        alerts.append("User is below eligible age for ration allotment")
        severity = "Medium"

    # Rule 2: Entitlement violation - Requested > allowed limit (Phase-8 D)
    current_month = datetime.now().strftime('%Y-%m')
    entitlements = get_user_entitlements(user_id, current_month)
    entitlement_dict = {row[0]: row[1] for row in entitlements} if entitlements else {}
    
    commodity_names = {
        "rice": "Rice",
        "wheat": "Wheat",
        "sugar": "Sugar",
        "kerosene": "Kerosene",
        "salt": "Salt",
        "soyabeanoil": "Soyabean Oil",
        "palmoil": "Palm Oil",
        "masoor": "Masoor",
        "moong": "Moong",
        "chana": "Chana"
    }
    
    for commodity_key, commodity_name in commodity_names.items():
        quantity = commodities_dict.get(commodity_key, 0)
        # Use entitlement if available, otherwise use COMMODITY_LIMITS
        limit = entitlement_dict.get(commodity_key, COMMODITY_LIMITS.get(commodity_key, 0))
        if quantity > limit:
            alerts.append(f"Entitlement violation: {commodity_name} requested ({quantity}) > allowed limit ({limit})")
            if quantity > limit * 1.5:  # More than 50% over limit
                severity = "High"
            elif severity != "High":
                severity = "Medium"

    # Rule 3: High-income loophole - High-income claiming full subsidy (Phase-8 D)
    if income_level == "High Income":
        total_requested = sum(commodities_dict.values())
        # Check if high-income user is requesting large quantities (potential abuse)
        if total_requested > 20:  # Arbitrary threshold for large request
            alerts.append("High-income loophole: High-income user requesting large quantities")
            severity = "Medium"

    # Rule 4: Repeated abnormal visits - >2 transactions/week (Phase-8 D)
    conn = get_connection()
    cur = conn.cursor()
    week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')
    cur.execute("""
        SELECT COUNT(*) FROM bills 
        WHERE user_id = ? AND timestamp >= ?
    """, (user_id, week_ago))
    weekly_count = cur.fetchone()[0]
    conn.close()
    
    if weekly_count >= 2:  # Already has 2+ transactions this week
        alerts.append(f"Repeated abnormal visits: {weekly_count + 1} transactions this week (>2 limit)")
        if weekly_count >= 3:
            severity = "High"
        elif severity != "High":
            severity = "Medium"

    # Rule 5: Shopkeeper collusion - Same shop → repeated flags (Phase-8 D)
    if shopkeeper_id:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT COUNT(*) FROM fraud_logs fl
            JOIN bills b ON fl.user_id = b.user_id
            WHERE b.user_id = ? AND b.shopkeeper_id = ?
        """, (user_id, shopkeeper_id))
        collusion_count = cur.fetchone()[0]
        conn.close()
        
        if collusion_count >= 2:
            alerts.append(f"Shopkeeper collusion: {collusion_count} previous fraud flags from same shop")
            severity = "High"

    # Rule 6: Aadhaar validity check
    if len(str(aadhaar)) != 12:
        alerts.append("Invalid Aadhaar detected")
        severity = "Medium"

    return alerts, severity
