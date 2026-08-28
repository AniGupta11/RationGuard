import streamlit as st
import sys
from pathlib import Path

# Fix imports based on project structure
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app.authentication import login_page
from app.registration import registration_page
from app.billing import billing_page, bill_history_page

# Dashboards
from app.dashboards.customer_dashboard import customer_dashboard
from app.dashboards.shopkeeper_dashboard import shopkeeper_dashboard
from app.dashboards.government_dashboard import government_dashboard

# Utils
from app.utils.db_ops import get_user_by_id, log_logout
from app.utils.security import check_session_expiry, require_login, sanitize_input
from app.utils.alert_system import display_notification_banner
from app.utils.streamlit_helpers import safe_rerun
from datetime import datetime


def load_role():
    """Load user role from session and database"""
    user_id = st.session_state.get("logged_in_user", None)
    if not user_id:
        return None
    
    # First check if role is in session state (faster)
    if "role" in st.session_state and st.session_state["role"]:
        return st.session_state["role"]
    
    # Check session expiry (Stage-8)
    try:
        check_session_expiry()
    except:
        pass
    
    user = get_user_by_id(user_id)
    if not user:
        return None
    
    # Role is at index 10: id, name, age, gender, address, aadhaar, ration_id, income_level, dependents, phone, role, created_at
    if len(user) > 10:
        role = user[10]
        # Store in session for faster access
        if role:
            st.session_state["role"] = role
        return role
    
    return None


def auto_redirect(role):
    """Auto-redirect to role-specific dashboard after login (Stage-1)"""
    if role == "Customer":
        st.session_state["page"] = "Customer Dashboard"
    elif role == "Shopkeeper":
        st.session_state["page"] = "Shopkeeper Dashboard"
    elif role == "Government Officer":
        st.session_state["page"] = "Government Dashboard"
    safe_rerun()


def main():
    st.set_page_config(page_title="RationGuard AI", layout="wide")

    # Sidebar Title & Status
    st.sidebar.title("RationGuard AI")

    role = load_role()

    # Display role + timestamp in sidebar (G - UI/UX Improvements, Stage-7)
    if role:
        role_display = {
            "Customer": "👤 Customer",
            "Shopkeeper": "🏪 Shopkeeper",
            "Government Officer": "🏛️ Government Officer"
        }
        role_str = str(role).strip()
        display_role = role_display.get(role_str, role_str)
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        st.sidebar.success(f"Logged in as {display_role}")
        st.sidebar.caption(f"Session: {current_time}")

    if "page" not in st.session_state:
        st.session_state["page"] = "Welcome"

    # Auto-Redirect after Login (Stage-1)
    if role and st.session_state["page"] in ["Welcome", "Login", "Register"]:
        auto_redirect(role)

    # ---------------- Sidebar Navigation (G - UI/UX: 3 Large Menu Sections) ---------------- #
    
    # 1. Authentication Section
    st.sidebar.markdown("### 🔐 Authentication")
    if role:
        user_id = st.session_state.get("logged_in_user")
        if st.sidebar.button("Logout", type="primary"):
            # Log logout (J - Security & Abuse Prevention, I - Logging)
            if user_id:
                try:
                    log_logout(user_id)
                except:
                    pass
            # Clear all session data (J - Security: Clear role data on logout)
            st.session_state.clear()
            st.session_state["page"] = "Welcome"
            # Prevent back navigation (J - Security: Disable browser back after logout)
            safe_rerun()
    else:
        if st.sidebar.button("Login"):
            st.session_state["page"] = "Login"
        if st.sidebar.button("Register"):
            st.session_state["page"] = "Register"

    # 2. Ration Services (Billing) Section
    if role:
        st.sidebar.markdown("### 🛒 Ration Services")
        role_str = str(role).strip()
        
        # Billing - Now available for Customers, Shopkeepers, and Government Officers
        if role_str in ["Customer", "Shopkeeper", "Government Officer"]:
            if st.sidebar.button("💳 Billing"):
                st.session_state["page"] = "Billing"
        
        # Bill History - All logged-in users
        if st.sidebar.button("📋 View Bills"):
            st.session_state["page"] = "Bill History"

    # 3. Analytics & Dashboards Section
    if role:
        st.sidebar.markdown("### 📊 Analytics & Dashboards")
        role_str = str(role).strip()
        
        # Customer sees only Customer Dashboard
        if role_str == "Customer":
            if st.sidebar.button("🏠 Customer Home"):
                st.session_state["page"] = "Customer Dashboard"
        
        # Shopkeeper sees only Shopkeeper Dashboard
        elif role_str == "Shopkeeper":
            if st.sidebar.button("🏪 Shopkeeper Portal"):
                st.session_state["page"] = "Shopkeeper Dashboard"
        
        # Government Officer sees ALL dashboards
        elif role_str == "Government Officer":
            if st.sidebar.button("🏛️ Govt Command Center"):
                st.session_state["page"] = "Government Dashboard"
            if st.sidebar.button("🏪 Shopkeeper Portal"):
                st.session_state["page"] = "Shopkeeper Dashboard"
            if st.sidebar.button("🏠 Customer Home"):
                st.session_state["page"] = "Customer Dashboard"
        
        # Support (Customer + Govt)
        if role_str in ["Customer", "Government Officer"]:
            st.sidebar.markdown("---")
            if st.sidebar.button("📞 Contact Support"):
                st.info("Support system will be implemented in next batch.")

    # ---------------- Page Routing with Security (J - Security: Prevent direct navigation) ---------------- #
    page = st.session_state.get("page", "Welcome")

    # Prevent unauthorized dashboard access (J - Security: Prevent direct navigation without login)
    dashboard_pages = ["Customer Dashboard", "Shopkeeper Dashboard", "Government Dashboard", 
                       "Billing", "Bill History"]
    if page in dashboard_pages and not role:
        st.error("⚠️ Access Denied: Please login first.")
        st.session_state["page"] = "Login"
        st.stop()

    # Role-based page access control (Stage-8)
    # Normalize role for comparison (handle case and whitespace)
    role_normalized = str(role).strip() if role else None
    
    # Strict access control:
    # 1. Customer can ONLY access Customer Dashboard
    # 2. Shopkeeper can ONLY access Shopkeeper Dashboard  
    # 3. Government Officer can access EVERYTHING
    
    if page == "Customer Dashboard":
        if role_normalized == "Customer":
            # Customer can access - allow
            pass
        elif role_normalized == "Government Officer":
            # Government Officer can access - allow
            pass
        else:
            # Deny access and redirect
            st.error(f"⚠️ Access Denied: Only Customers and Government Officers can access Customer Dashboard. Your role: {role}")
            if role_normalized == "Shopkeeper":
                st.session_state["page"] = "Shopkeeper Dashboard"
                safe_rerun()
            st.stop()
    
    if page == "Shopkeeper Dashboard":
        if role_normalized == "Shopkeeper":
            # Shopkeeper can access - allow
            pass
        elif role_normalized == "Government Officer":
            # Government Officer can access - allow
            pass
        else:
            # Deny access and redirect
            st.error(f"⚠️ Access Denied: Only Shopkeepers and Government Officers can access Shopkeeper Dashboard. Your role: {role}")
            if role_normalized == "Customer":
                st.session_state["page"] = "Customer Dashboard"
                safe_rerun()
            st.stop()
    
    if page == "Government Dashboard":
        if role_normalized == "Government Officer":
            # Government Officer can access - allow
            pass
        else:
            # Deny access and redirect
            st.error(f"⚠️ Access Denied: Only Government Officers can access Government Dashboard. Your role: {role}")
            if role_normalized == "Customer":
                st.session_state["page"] = "Customer Dashboard"
                safe_rerun()
            elif role_normalized == "Shopkeeper":
                st.session_state["page"] = "Shopkeeper Dashboard"
                safe_rerun()
            st.stop()
    
    if page == "Billing":
        if role_normalized in ["Customer", "Shopkeeper", "Government Officer"]:
            pass
        else:
            st.error(f"⚠️ Access Denied: Billing is available for Customers, Shopkeepers and Government Officers. Your role: {role}")
            st.stop()

    # Display alerts banner (Stage-4)
    if role and page in dashboard_pages:
        user_id = st.session_state.get("logged_in_user")
        if user_id:
            display_notification_banner(user_id, role)

    # Route to appropriate page
    if page == "Welcome":
        show_welcome()
    elif page == "Login":
        login_page()
    elif page == "Register":
        registration_page()
    elif page == "Billing":
        billing_page()
    elif page == "Bill History":
        bill_history_page()
    elif page == "Customer Dashboard":
        customer_dashboard()
    elif page == "Shopkeeper Dashboard":
        shopkeeper_dashboard()
    elif page == "Government Dashboard":
        government_dashboard()
    else:
        show_welcome()


def show_welcome():
    st.title("Welcome to RationGuard AI")
    st.write("AI-based Ration Distribution and Fraud Detection System")
    
    role = load_role()
    if not role:
        st.info("Please login or register to continue")


if __name__ == "__main__":
    main()
