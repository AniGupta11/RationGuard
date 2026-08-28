import sqlite3
import os
from datetime import datetime

DB_DIR = "database"
DB_PATH = os.path.join(DB_DIR, "rationguard.db")

def get_connection():
    if not os.path.exists(DB_DIR):
        os.makedirs(DB_DIR)
    return sqlite3.connect(DB_PATH)


# ---------------- CREATE & UPDATE TABLES ---------------- #

def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # Users table (role included)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            age INTEGER,
            gender TEXT,
            address TEXT,
            aadhaar TEXT UNIQUE,
            ration_id TEXT UNIQUE,
            income_level TEXT,
            dependents INTEGER,
            phone TEXT,
            role TEXT DEFAULT 'Customer',
            created_at TEXT
        )
    """)

    # Ensure role column exists (safe migration)
    cur.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in cur.fetchall()]

    bills_renames = {
        "toordal_qty": "moong_qty",
        "chanadal_qty": "chana_qty",
        "uraddal_qty": "masoor_qty",
        "mustardoil_qty": "palmoil_qty",
        "sunfloweroil_qty": "soyabeanoil_qty",
    }
    for old_col, new_col in bills_renames.items():
        if old_col in columns and new_col not in columns:
            try:
                cur.execute(f"ALTER TABLE bills RENAME COLUMN {old_col} TO {new_col}")
                columns = [new_col if c == old_col else c for c in columns]
            except sqlite3.OperationalError:
                pass
    if "role" not in columns:
        cur.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'Customer'")
    
    # Add subsidy_eligible column (H - Database Enhancements)
    if "subsidy_eligible" not in columns:
        cur.execute("ALTER TABLE users ADD COLUMN subsidy_eligible INTEGER DEFAULT 1")
    
    # Add login tracking table (I - Logging & Monitoring)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS login_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            login_timestamp TEXT,
            logout_timestamp TEXT,
            ip_address TEXT
        )
    """)
    
    # Add monthly usage tracking table (I - Logging & Monitoring, 10 Commodities)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS monthly_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            month_year TEXT,
            rice_used REAL DEFAULT 0,
            wheat_used REAL DEFAULT 0,
            sugar_used REAL DEFAULT 0,
            kerosene_used REAL DEFAULT 0,
            salt_used REAL DEFAULT 0,
            soyabeanoil_used REAL DEFAULT 0,
            palmoil_used REAL DEFAULT 0,
            masoor_used REAL DEFAULT 0,
            moong_used REAL DEFAULT 0,
            chana_used REAL DEFAULT 0,
            total_bills INTEGER DEFAULT 0
        )
    """)
    
    # Migrate monthly_usage table if needed
    cur.execute("PRAGMA table_info(monthly_usage)")
    usage_columns = [col[1] for col in cur.fetchall()]

    usage_renames = {
        "toordal_used": "moong_used",
        "chanadal_used": "chana_used",
        "uraddal_used": "masoor_used",
        "mustardoil_used": "palmoil_used",
        "sunfloweroil_used": "soyabeanoil_used",
    }
    for old_col, new_col in usage_renames.items():
        if old_col in usage_columns and new_col not in usage_columns:
            try:
                cur.execute(f"ALTER TABLE monthly_usage RENAME COLUMN {old_col} TO {new_col}")
                usage_columns = [new_col if c == old_col else c for c in usage_columns]
            except sqlite3.OperationalError:
                pass
    new_commodity_columns = [
        "kerosene_used", "salt_used", "soyabeanoil_used", "palmoil_used",
        "masoor_used", "moong_used", "chana_used"
    ]
    for col_name in new_commodity_columns:
        if col_name not in usage_columns:
            cur.execute(f"ALTER TABLE monthly_usage ADD COLUMN {col_name} REAL DEFAULT 0")

    # Fraud logs table (10 Commodities, Phase-8 K: Alert Severity)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS fraud_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            timestamp TEXT,
            reason TEXT,
            ml_score REAL,
            severity TEXT DEFAULT 'Low',
            rice_qty REAL DEFAULT 0,
            wheat_qty REAL DEFAULT 0,
            sugar_qty REAL DEFAULT 0,
            kerosene_qty REAL DEFAULT 0,
            salt_qty REAL DEFAULT 0,
            soyabeanoil_qty REAL DEFAULT 0,
            palmoil_qty REAL DEFAULT 0,
            masoor_qty REAL DEFAULT 0,
            moong_qty REAL DEFAULT 0,
            chana_qty REAL DEFAULT 0
        )
    """)
    
    # Migrate fraud_logs table if needed (add new commodity columns and severity)
    cur.execute("PRAGMA table_info(fraud_logs)")
    fraud_columns = [col[1] for col in cur.fetchall()]

    fraud_renames = {
        "toordal_qty": "moong_qty",
        "chanadal_qty": "chana_qty",
        "uraddal_qty": "masoor_qty",
        "mustardoil_qty": "palmoil_qty",
        "sunfloweroil_qty": "soyabeanoil_qty",
    }
    for old_col, new_col in fraud_renames.items():
        if old_col in fraud_columns and new_col not in fraud_columns:
            try:
                cur.execute(f"ALTER TABLE fraud_logs RENAME COLUMN {old_col} TO {new_col}")
                fraud_columns = [new_col if c == old_col else c for c in fraud_columns]
            except sqlite3.OperationalError:
                pass
    new_fraud_commodity_columns = [
        "kerosene_qty", "salt_qty", "soyabeanoil_qty", "palmoil_qty",
        "masoor_qty", "moong_qty", "chana_qty"
    ]
    for col_name in new_fraud_commodity_columns:
        if col_name not in fraud_columns:
            cur.execute(f"ALTER TABLE fraud_logs ADD COLUMN {col_name} REAL DEFAULT 0")
    
    # Add severity column if it doesn't exist (Phase-8 K migration)
    if "severity" not in fraud_columns:
        cur.execute("ALTER TABLE fraud_logs ADD COLUMN severity TEXT DEFAULT 'Low'")

    # Bills table (upgraded schema - Stage-5, H - Database Enhancements, 10 Commodities)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS bills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            shopkeeper_id INTEGER,
            timestamp TEXT,
            rice_qty REAL DEFAULT 0,
            wheat_qty REAL DEFAULT 0,
            sugar_qty REAL DEFAULT 0,
            kerosene_qty REAL DEFAULT 0,
            salt_qty REAL DEFAULT 0,
            soyabeanoil_qty REAL DEFAULT 0,
            palmoil_qty REAL DEFAULT 0,
            masoor_qty REAL DEFAULT 0,
            moong_qty REAL DEFAULT 0,
            chana_qty REAL DEFAULT 0,
            commodity_qty TEXT,
            total_amount REAL,
            subsidy_availed REAL DEFAULT 0,
            subsidy_eligible BOOLEAN DEFAULT 0,
            file_path TEXT,
            ml_score REAL,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (shopkeeper_id) REFERENCES users(id)
        )
    """)
    
    # Migrate existing bills table if needed
    cur.execute("PRAGMA table_info(bills)")
    columns = [col[1] for col in cur.fetchall()]
    commodity_columns = [
        "shopkeeper_id", "commodity_qty", "subsidy_availed", "subsidy_eligible", "ml_score",
        "kerosene_qty", "salt_qty", "soyabeanoil_qty", "palmoil_qty",
        "masoor_qty", "moong_qty", "chana_qty"
    ]
    for col_name in commodity_columns:
        if col_name not in columns:
            if col_name.endswith("_qty"):
                cur.execute(f"ALTER TABLE bills ADD COLUMN {col_name} REAL DEFAULT 0")
            elif col_name == "shopkeeper_id":
                cur.execute("ALTER TABLE bills ADD COLUMN shopkeeper_id INTEGER")
            elif col_name == "commodity_qty":
                cur.execute("ALTER TABLE bills ADD COLUMN commodity_qty TEXT")
            elif col_name == "subsidy_availed":
                cur.execute("ALTER TABLE bills ADD COLUMN subsidy_availed REAL DEFAULT 0")
            elif col_name == "subsidy_eligible":
                cur.execute("ALTER TABLE bills ADD COLUMN subsidy_eligible BOOLEAN DEFAULT 0")
            elif col_name == "ml_score":
                cur.execute("ALTER TABLE bills ADD COLUMN ml_score REAL")

    # Entitlements table (Phase-8 C: Family-size Based Monthly Entitlement Engine)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS entitlements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            commodity TEXT,
            entitlement_qty REAL,
            month_year TEXT,
            entitlement_percent REAL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    # Shop stock table (Phase-8 E: Shop Stock Management)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS shop_stock (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shopkeeper_id INTEGER,
            commodity TEXT,
            allocated_qty REAL DEFAULT 0,
            used_qty REAL DEFAULT 0,
            month TEXT,
            FOREIGN KEY (shopkeeper_id) REFERENCES users(id)
        )
    """)

    # Notifications table for alerting
    cur.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            message TEXT,
            channel TEXT,
            type TEXT,
            month_year TEXT,
            status TEXT,
            created_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS dependents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT,
            relation TEXT,
            age INTEGER,
            created_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    conn.commit()
    conn.close()


# ---------------- INSERT OPERATIONS ---------------- #

def create_user(name, age, gender, address, aadhaar, ration_id,
                income_level, dependents, phone):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO users
        (name, age, gender, address, aadhaar, ration_id,
         income_level, dependents, phone, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
    (name, age, gender, address, aadhaar, ration_id,
     income_level, dependents, phone,
     datetime.now().isoformat(timespec="seconds"))
    )

    conn.commit()
    user_id = cur.lastrowid
    conn.close()
    return user_id


# ---------------- DELETE OPERATIONS ---------------- #

def delete_user(user_id: int):
    """
    Remove a user and related records.
    Safely ignores tables if they are missing columns.
    """
    conn = get_connection()
    cur = conn.cursor()

    cleanup_targets = [
        ("dependents", "user_id"),
        ("entitlements", "user_id"),
        ("monthly_usage", "user_id"),
        ("notifications", "user_id"),
        ("fraud_logs", "user_id"),
        ("bills", "user_id"),
        ("bills", "shopkeeper_id"),
        ("login_logs", "user_id"),
        ("shop_stock", "shopkeeper_id"),
    ]

    for table, column in cleanup_targets:
        try:
            cur.execute(f"DELETE FROM {table} WHERE {column} = ?", (user_id,))
        except sqlite3.OperationalError:
            # Table or column might not exist in older schemas; skip instead of crashing.
            continue

    cur.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()


def log_fraud(user_id, reason, ml_score, commodities_dict, severity="Low"):
    """
    Log fraud with all 10 commodities and severity level (Phase-8 K)
    Severity: "High", "Medium", "Low"
    """
    conn = get_connection()
    cur = conn.cursor()
    
    # Extract all 10 commodity quantities
    rice = commodities_dict.get("rice", 0)
    wheat = commodities_dict.get("wheat", 0)
    sugar = commodities_dict.get("sugar", 0)
    kerosene = commodities_dict.get("kerosene", 0)
    masoor = commodities_dict.get("masoor", 0)
    moong = commodities_dict.get("moong", 0)
    chana = commodities_dict.get("chana", 0)
    salt = commodities_dict.get("salt", 0)
    palmoil = commodities_dict.get("palmoil", 0)
    soyabeanoil = commodities_dict.get("soyabeanoil", 0)

    cur.execute("""
        INSERT INTO fraud_logs
        (user_id, timestamp, reason, ml_score, severity, rice_qty, wheat_qty, sugar_qty,
         kerosene_qty, salt_qty, soyabeanoil_qty, palmoil_qty, masoor_qty,
         moong_qty, chana_qty)
        VALUES (?, datetime('now','localtime'), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
    (user_id, reason, ml_score, severity, rice, wheat, sugar, kerosene, salt,
     soyabeanoil, palmoil, masoor, moong, chana))

    conn.commit()
    conn.close()


def save_bill(user_id, shopkeeper_id, commodities_dict, total_amount, 
              file_path, subsidy_availed=0, subsidy_eligible=False, ml_score=None, commodity_qty=None):
    """Save bill with upgraded schema (H - Database Enhancements, 10 Commodities)"""
    conn = get_connection()
    cur = conn.cursor()

    # Extract commodity quantities with defaults
    rice = commodities_dict.get("rice", 0)
    wheat = commodities_dict.get("wheat", 0)
    sugar = commodities_dict.get("sugar", 0)
    kerosene = commodities_dict.get("kerosene", 0)
    masoor = commodities_dict.get("masoor", 0)
    moong = commodities_dict.get("moong", 0)
    chana = commodities_dict.get("chana", 0)
    salt = commodities_dict.get("salt", 0)
    palmoil = commodities_dict.get("palmoil", 0)
    soyabeanoil = commodities_dict.get("soyabeanoil", 0)

    cur.execute("""
        INSERT INTO bills
        (user_id, shopkeeper_id, timestamp, rice_qty, wheat_qty, sugar_qty,
         kerosene_qty, salt_qty, soyabeanoil_qty, palmoil_qty, masoor_qty,
         moong_qty, chana_qty, commodity_qty, total_amount, 
         subsidy_availed, subsidy_eligible, file_path, ml_score)
        VALUES (?, ?, datetime('now','localtime'), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
    (user_id, shopkeeper_id, rice, wheat, sugar, kerosene, salt, soyabeanoil,
     palmoil, masoor, moong, chana, commodity_qty, total_amount, 
     subsidy_availed, 1 if subsidy_eligible else 0, file_path, ml_score))

    conn.commit()
    bill_id = cur.lastrowid
    
    # Update monthly usage tracking (I - Logging & Monitoring)
    update_monthly_usage(user_id, commodities_dict)
    
    conn.close()
    return bill_id


# ---------------- FETCH OPERATIONS ---------------- #

def get_user_by_aadhaar_ration(aadhaar, ration_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, name, age, gender, address, aadhaar,
        ration_id, income_level, dependents, phone, role, created_at
        FROM users
        WHERE aadhaar = ? AND ration_id = ?
    """, (aadhaar, ration_id))

    row = cur.fetchone()
    conn.close()
    return row


def get_user_by_aadhaar(aadhaar):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM users WHERE aadhaar = ?", (aadhaar,))
    row = cur.fetchone()
    conn.close()
    return row


def get_user_by_ration(ration_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM users WHERE ration_id = ?", (ration_id,))
    row = cur.fetchone()
    conn.close()
    return row


def get_user_by_id(user_id: int):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, name, age, gender, address, aadhaar,
        ration_id, income_level, dependents, phone, role, created_at
        FROM users
        WHERE id = ?
    """, (user_id,))

    row = cur.fetchone()
    conn.close()
    return row


def get_users_by_role(role: str):
    """Return list of users (id, name) for a specific role."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, name
        FROM users
        WHERE role = ?
        ORDER BY name COLLATE NOCASE
        """,
        (role,)
    )
    rows = cur.fetchall()
    conn.close()
    return rows
# ---------------- FETCH FOR DASHBOARDS ---------------- #

def get_user_bills(user_id):
    """Get bills for a specific customer (10 Commodities)"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT bills.id, bills.timestamp, 
               bills.rice_qty, bills.wheat_qty, bills.sugar_qty,
               bills.kerosene_qty, bills.salt_qty, bills.soyabeanoil_qty,
               bills.palmoil_qty, bills.masoor_qty, bills.moong_qty,
               bills.chana_qty, bills.total_amount, bills.subsidy_availed, 
               bills.file_path, bills.ml_score, users.name as shopkeeper_name
        FROM bills
        JOIN users ON bills.shopkeeper_id = users.id
        WHERE bills.user_id = ?
        ORDER BY bills.timestamp DESC
    """, (user_id,))
    rows = cur.fetchall()
    conn.close()
    return rows


def get_shopkeeper_bills(shopkeeper_id):
    """Get bills generated by a specific shopkeeper (10 Commodities)"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT bills.id, users.name as customer_name, bills.timestamp,
               bills.rice_qty, bills.wheat_qty, bills.sugar_qty,
               bills.kerosene_qty, bills.salt_qty, bills.soyabeanoil_qty,
               bills.palmoil_qty, bills.masoor_qty, bills.moong_qty,
               bills.chana_qty, bills.total_amount, bills.subsidy_availed, bills.ml_score
        FROM bills
        JOIN users ON bills.user_id = users.id
        WHERE bills.shopkeeper_id = ?
        ORDER BY bills.timestamp DESC
    """, (shopkeeper_id,))
    rows = cur.fetchall()
    conn.close()
    return rows


def get_shop_stock(shopkeeper_id):
    """Fetch shop stock allocation and usage for a shopkeeper"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT commodity, allocated_qty, used_qty, month
        FROM shop_stock
        WHERE shopkeeper_id = ?
        ORDER BY month DESC, commodity ASC
    """,
        (shopkeeper_id,),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def save_dependents(user_id, dependents):
    conn = get_connection()
    cur = conn.cursor()
    for d in dependents:
        cur.execute(
            """
            INSERT INTO dependents (user_id, name, relation, age, created_at)
            VALUES (?, ?, ?, ?, datetime('now','localtime'))
            """,
            (user_id, d.get("name"), d.get("relation"), int(d.get("age", 0)))
        )
    conn.commit()
    conn.close()


def get_dependents(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT name, relation, age FROM dependents
        WHERE user_id = ? ORDER BY age DESC, name ASC
        """,
        (user_id,)
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def delete_dependents_for_user(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM dependents WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


def get_all_bills():
    """Get all bills (for Government, 10 Commodities)"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT bills.id, 
               customer.name as customer_name,
               shopkeeper.name as shopkeeper_name,
               bills.timestamp,
               bills.rice_qty, bills.wheat_qty, bills.sugar_qty,
               bills.kerosene_qty, bills.salt_qty, bills.soyabeanoil_qty,
               bills.palmoil_qty, bills.masoor_qty, bills.moong_qty,
               bills.chana_qty, bills.total_amount, bills.subsidy_availed, bills.ml_score
        FROM bills
        JOIN users as customer ON bills.user_id = customer.id
        JOIN users as shopkeeper ON bills.shopkeeper_id = shopkeeper.id
        ORDER BY bills.timestamp DESC
    """)
    rows = cur.fetchall()
    conn.close()
    return rows


def get_fraud_logs():
    """Get all fraud logs with all 10 commodities"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT fraud_logs.id, users.name, fraud_logs.timestamp, 
               fraud_logs.reason, fraud_logs.ml_score,
               fraud_logs.rice_qty, fraud_logs.wheat_qty, fraud_logs.sugar_qty,
               fraud_logs.kerosene_qty, fraud_logs.salt_qty, fraud_logs.soyabeanoil_qty,
               fraud_logs.palmoil_qty, fraud_logs.masoor_qty, fraud_logs.moong_qty,
               fraud_logs.chana_qty
        FROM fraud_logs
        JOIN users ON fraud_logs.user_id = users.id
        ORDER BY fraud_logs.timestamp DESC
    """)
    rows = cur.fetchall()
    conn.close()
    return rows


def get_user_fraud_alerts(user_id):
    """Get fraud alerts for a specific user"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, timestamp, reason, ml_score
        FROM fraud_logs
        WHERE user_id = ?
        ORDER BY timestamp DESC
        LIMIT 10
    """, (user_id,))
    rows = cur.fetchall()
    conn.close()
    return rows


def has_notification(user_id, type, month_year):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT COUNT(*) FROM notifications
        WHERE user_id = ? AND type = ? AND month_year = ?
    """,
        (user_id, type, month_year),
    )
    count = cur.fetchone()[0]
    conn.close()
    return count > 0


def log_notification(user_id, message, channel="whatsapp", type="quota_30", month_year=None, status="queued"):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO notifications (user_id, message, channel, type, month_year, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, datetime('now','localtime'))
    """,
        (user_id, message, channel, type, month_year, status),
    )
    conn.commit()
    nid = cur.lastrowid
    conn.close()
    return nid


def update_notification_status(notification_id, status):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE notifications SET status = ? WHERE id = ?
    """,
        (status, notification_id),
    )
    conn.commit()
    conn.close()


def get_total_beneficiaries():
    """Get total number of beneficiaries"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users WHERE role = 'Customer'")
    count = cur.fetchone()[0]
    conn.close()
    return count


def get_fraud_trend(days=30):
    """Get fraud detection trend"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT DATE(timestamp) as date, COUNT(*) as count
        FROM fraud_logs
        WHERE timestamp >= datetime('now', '-' || ? || ' days')
        GROUP BY DATE(timestamp)
        ORDER BY date DESC
    """, (days,))
    rows = cur.fetchall()
    conn.close()
    return rows


def get_commodity_stats():
    """Get commodity demand and subsidy statistics (10 Commodities)"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT 
            SUM(rice_qty) as total_rice,
            SUM(wheat_qty) as total_wheat,
            SUM(sugar_qty) as total_sugar,
            SUM(kerosene_qty) as total_kerosene,
            SUM(salt_qty) as total_salt,
            SUM(soyabeanoil_qty) as total_soyabeanoil,
            SUM(palmoil_qty) as total_palmoil,
            SUM(masoor_qty) as total_masoor,
            SUM(moong_qty) as total_moong,
            SUM(chana_qty) as total_chana,
            SUM(subsidy_availed) as total_subsidy,
            COUNT(*) as total_bills
        FROM bills
    """)
    row = cur.fetchone()
    conn.close()
    return row


def get_fraud_by_shopkeeper():
    """Get ranking of most fraud-detected shops"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT 
            shopkeeper.name as shopkeeper_name,
            COUNT(fraud_logs.id) as fraud_count
        FROM fraud_logs
        JOIN bills ON fraud_logs.user_id = bills.user_id
        JOIN users as shopkeeper ON bills.shopkeeper_id = shopkeeper.id
        GROUP BY shopkeeper.id, shopkeeper.name
        ORDER BY fraud_count DESC
    """)
    rows = cur.fetchall()
    conn.close()
    return rows


# ---------------- LOGGING & MONITORING (I) ---------------- #

def log_login(user_id, ip_address=None):
    """Log user login (I - Logging & Monitoring)"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO login_logs (user_id, login_timestamp, ip_address)
        VALUES (?, datetime('now','localtime'), ?)
    """, (user_id, ip_address))
    conn.commit()
    conn.close()


def log_logout(user_id):
    """Log user logout (I - Logging & Monitoring)"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE login_logs 
        SET logout_timestamp = datetime('now','localtime')
        WHERE user_id = ? AND logout_timestamp IS NULL
        ORDER BY id DESC LIMIT 1
    """, (user_id,))
    conn.commit()
    conn.close()


def get_fraud_attempts_count(user_id):
    """Get number of fraud attempts per user (I - Logging & Monitoring)"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM fraud_logs WHERE user_id = ?", (user_id,))
    count = cur.fetchone()[0]
    conn.close()
    return count


def update_monthly_usage(user_id, commodities_dict):
    """Update monthly ration usage tracking (I - Logging & Monitoring, 10 Commodities)"""
    conn = get_connection()
    cur = conn.cursor()
    month_year = datetime.now().strftime("%Y-%m")
    
    # Extract commodity quantities with defaults
    rice = commodities_dict.get("rice", 0)
    wheat = commodities_dict.get("wheat", 0)
    sugar = commodities_dict.get("sugar", 0)
    kerosene = commodities_dict.get("kerosene", 0)
    masoor = commodities_dict.get("masoor", 0)
    moong = commodities_dict.get("moong", 0)
    chana = commodities_dict.get("chana", 0)
    salt = commodities_dict.get("salt", 0)
    palmoil = commodities_dict.get("palmoil", 0)
    soyabeanoil = commodities_dict.get("soyabeanoil", 0)
    
    # Check if record exists
    cur.execute("""
        SELECT id FROM monthly_usage 
        WHERE user_id = ? AND month_year = ?
    """, (user_id, month_year))
    existing = cur.fetchone()
    
    if existing:
        # Update existing record
        cur.execute("""
            UPDATE monthly_usage
            SET rice_used = rice_used + ?,
                wheat_used = wheat_used + ?,
                sugar_used = sugar_used + ?,
                kerosene_used = kerosene_used + ?,
                salt_used = salt_used + ?,
                soyabeanoil_used = soyabeanoil_used + ?,
                palmoil_used = palmoil_used + ?,
                masoor_used = masoor_used + ?,
                moong_used = moong_used + ?,
                chana_used = chana_used + ?,
                total_bills = total_bills + 1
            WHERE user_id = ? AND month_year = ?
        """, (rice, wheat, sugar, kerosene, salt, soyabeanoil, palmoil,
              masoor, moong, chana, user_id, month_year))
    else:
        # Create new record
        cur.execute("""
            INSERT INTO monthly_usage 
            (user_id, month_year, rice_used, wheat_used, sugar_used,
             kerosene_used, salt_used, soyabeanoil_used, palmoil_used,
             masoor_used, moong_used, chana_used, total_bills)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        """, (user_id, month_year, rice, wheat, sugar, kerosene, salt,
              soyabeanoil, palmoil, masoor, moong, chana))
    
    conn.commit()
    conn.close()


def get_monthly_usage(user_id, month_year=None):
    """Get monthly usage for a user (I - Logging & Monitoring)"""
    conn = get_connection()
    cur = conn.cursor()
    
    if month_year:
        cur.execute("""
            SELECT * FROM monthly_usage 
            WHERE user_id = ? AND month_year = ?
        """, (user_id, month_year))
    else:
        cur.execute("""
            SELECT * FROM monthly_usage 
            WHERE user_id = ?
            ORDER BY month_year DESC
        """, (user_id,))
    
    rows = cur.fetchall()
    conn.close()
    return rows


def get_all_monthly_usage_stats():
    """Get all monthly usage stats for Government dashboard (I - Logging & Monitoring, 10 Commodities)"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT month_year, 
               SUM(rice_used) as total_rice,
               SUM(wheat_used) as total_wheat,
               SUM(sugar_used) as total_sugar,
               SUM(kerosene_used) as total_kerosene,
               SUM(salt_used) as total_salt,
               SUM(soyabeanoil_used) as total_soyabeanoil,
               SUM(palmoil_used) as total_palmoil,
               SUM(masoor_used) as total_masoor,
               SUM(moong_used) as total_moong,
               SUM(chana_used) as total_chana,
               SUM(total_bills) as total_bills
        FROM monthly_usage
        GROUP BY month_year
        ORDER BY month_year DESC
    """)
    rows = cur.fetchall()
    conn.close()
    return rows


# Initialize DB when imported
init_db()
