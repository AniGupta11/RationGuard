import streamlit as st
import re
from app.utils.db_ops import get_user_by_id


def sanitize_input(text):
    """Prevent SQL injection by sanitizing input (Stage-8)"""
    if not text:
        return ""
    # Remove SQL injection patterns
    dangerous_patterns = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE)\b)",
        r"(--|#|/\*|\*/)",
        r"(\b(OR|AND)\s+\d+\s*=\s*\d+)",
        r"('|;|--|\|)"
    ]
    
    sanitized = str(text)
    for pattern in dangerous_patterns:
        sanitized = re.sub(pattern, "", sanitized, flags=re.IGNORECASE)
    
    return sanitized.strip()


def check_session_expiry():
    """Check if session is still valid on refresh (Stage-8)"""
    if "logged_in_user" in st.session_state:
        user_id = st.session_state.get("logged_in_user")
        if user_id:
            user = get_user_by_id(user_id)
            if not user:
                # User deleted or invalid
                st.session_state.clear()
                st.error("Session expired. Please login again.")
                st.stop()
            return True
    return False


def require_login(required_role=None):
    """Require valid login and optionally specific role (Stage-8)"""
    if "logged_in_user" not in st.session_state:
        st.error("⚠️ Access Denied: Please login first.")
        st.session_state["page"] = "Login"
        st.stop()
    
    # Check session validity
    check_session_expiry()
    
    if required_role:
        user_id = st.session_state.get("logged_in_user")
        user = get_user_by_id(user_id)
        if user and user[-1] != required_role:
            st.error(f"⚠️ Access Denied: {required_role} role required.")
            st.stop()
    
    return True


def prevent_manual_navigation():
    """Prevent users from manually switching pages via URL (Stage-8)"""
    # This is handled by session state in main.py
    # Users can only navigate through sidebar buttons
    pass

