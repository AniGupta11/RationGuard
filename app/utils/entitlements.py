"""
Phase-8 C: Family-size Based Monthly Entitlement Engine
Formula: entitlement_qty = (dependents + 1) x 5 x entitlement%
- Per member max entitlement: 5 kg/L
- Per member min entitlement: 2.5 kg/L
- Entitlement % based on income level
"""
from app.utils.db_ops import get_connection
from datetime import datetime


def get_entitlement_percent(income_level):
    """
    Get entitlement percentage based on income level
    - Low Income: 100% (full entitlement)
    - Middle Income: 70% (reduced entitlement)
    - High Income: 40% (minimal entitlement)
    """
    if income_level == "Low Income":
        return 1.0  # 100%
    elif income_level == "Middle Income":
        return 0.70  # 70%
    elif income_level == "High Income":
        return 0.40  # 40%
    else:
        return 0.5  # Default 50%


def calculate_entitlement(dependents, income_level, commodity_type="general"):
    """
    Calculate monthly entitlement for a user
    Formula: entitlement_qty = (dependents + 1) x 5 x entitlement%
    
    Args:
        dependents: Number of dependents
        income_level: Low Income, Middle Income, or High Income
        commodity_type: Type of commodity (for future use)
    
    Returns:
        float: Entitlement quantity in kg/L
    """
    family_size = dependents + 1  # Include the head of family
    base_entitlement = 5.0  # Per member max entitlement (5 kg/L)
    entitlement_percent = get_entitlement_percent(income_level)
    
    entitlement_qty = family_size * base_entitlement * entitlement_percent
    
    # Ensure minimum entitlement (2.5 kg/L per member)
    min_entitlement = family_size * 2.5
    entitlement_qty = max(entitlement_qty, min_entitlement)
    
    return entitlement_qty


def get_user_entitlements(user_id, month_year=None):
    """
    Get entitlements for a user for a specific month
    """
    if not month_year:
        month_year = datetime.now().strftime('%Y-%m')
    
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT commodity, entitlement_qty, entitlement_percent
        FROM entitlements
        WHERE user_id = ? AND month_year = ?
    """, (user_id, month_year))
    rows = cur.fetchall()
    conn.close()
    return rows


def get_remaining_quota(user_id, month_year=None):
    """
    Phase-9: Get remaining quota for all commodities
    Returns: dict with commodity -> remaining_qty
    """
    if not month_year:
        month_year = datetime.now().strftime('%Y-%m')
    
    conn = get_connection()
    cur = conn.cursor()
    
    # Get entitlements
    cur.execute("""
        SELECT commodity, entitlement_qty
        FROM entitlements
        WHERE user_id = ? AND month_year = ?
    """, (user_id, month_year))
    entitlements = cur.fetchall()
    entitlement_dict = {row[0]: row[1] for row in entitlements}
    
    # Get used quantities from monthly_usage
    cur.execute("""
        SELECT rice_used, wheat_used, sugar_used, kerosene_used, salt_used,
               soyabeanoil_used, palmoil_used, masoor_used, moong_used, chana_used
        FROM monthly_usage
        WHERE user_id = ? AND month_year = ?
    """, (user_id, month_year))
    usage = cur.fetchone()
    conn.close()
    
    # Calculate remaining
    commodities = [
        "rice", "wheat", "sugar", "kerosene", "salt",
        "soyabeanoil", "palmoil", "masoor", "moong", "chana"
    ]
    
    remaining = {}
    for idx, commodity in enumerate(commodities):
        entitlement = entitlement_dict.get(commodity, 0)
        used = usage[idx] if usage else 0
        remaining[commodity] = max(0, entitlement - (used or 0))
    
    return remaining


def create_user_entitlements(user_id, dependents, income_level, month_year=None):
    """
    Create entitlements for all 10 commodities for a user
    """
    if not month_year:
        month_year = datetime.now().strftime('%Y-%m')
    
    entitlement_percent = get_entitlement_percent(income_level)
    base_entitlement = calculate_entitlement(dependents, income_level)
    
    commodities = [
        "rice", "wheat", "sugar", "kerosene", "salt",
        "soyabeanoil", "palmoil", "masoor", "moong", "chana"
    ]
    
    conn = get_connection()
    cur = conn.cursor()
    
    # Delete existing entitlements for this month
    cur.execute("DELETE FROM entitlements WHERE user_id = ? AND month_year = ?", 
                (user_id, month_year))
    
    # Insert entitlements for all commodities
    for commodity in commodities:
        cur.execute("""
            INSERT INTO entitlements (user_id, commodity, entitlement_qty, month_year, entitlement_percent)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, commodity, base_entitlement, month_year, entitlement_percent))
    
    conn.commit()
    conn.close()
    return True


def auto_reset_monthly_entitlements():
    """
    Phase-9: Auto-reset entitlements at start of each month
    This should be called by a scheduled task
    """
    current_month = datetime.now().strftime('%Y-%m')
    
    conn = get_connection()
    cur = conn.cursor()
    
    # Get all customers
    cur.execute("""
        SELECT id, dependents, income_level
        FROM users
        WHERE role = 'Customer'
    """)
    customers = cur.fetchall()
    conn.close()
    
    # Create entitlements for current month for all customers
    for customer in customers:
        user_id, dependents, income_level = customer
        try:
            create_user_entitlements(user_id, dependents, income_level, current_month)
        except:
            pass  # Skip if already exists
    
    return len(customers)


def ensure_user_entitlements_current_month(user_id):
    month_year = datetime.now().strftime('%Y-%m')
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(1) FROM entitlements
        WHERE user_id = ? AND month_year = ?
    """, (user_id, month_year))
    exists = cur.fetchone()[0] or 0
    if exists == 0:
        cur.execute("SELECT dependents, income_level FROM users WHERE id = ?", (user_id,))
        row = cur.fetchone()
        if row:
            dependents, income_level = row
            cur.close()
            conn.close()
            return create_user_entitlements(user_id, dependents, income_level, month_year)
    conn.close()
    return True


def ensure_all_customers_entitlements_current_month():
    month_year = datetime.now().strftime('%Y-%m')
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, dependents, income_level
        FROM users
        WHERE role = 'Customer'
    """)
    customers = cur.fetchall()
    ensured = 0
    for user_id, dependents, income_level in customers:
        cur.execute("""
            SELECT COUNT(1) FROM entitlements
            WHERE user_id = ? AND month_year = ?
        """, (user_id, month_year))
        exists = cur.fetchone()[0] or 0
        if exists == 0:
            create_user_entitlements(user_id, dependents, income_level, month_year)
            ensured += 1
    conn.close()
    return ensured

