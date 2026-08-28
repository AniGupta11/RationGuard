import streamlit as st
from app.utils.face_recognition_module import recognize_face
from app.utils.db_ops import get_user_by_id, get_user_by_aadhaar_ration, log_login
from app.utils.streamlit_helpers import safe_rerun


def login_page():
    st.title("Login")
    st.write("Login using Face Recognition or Aadhaar + Ration Card.")

    # --------------- FACE LOGIN --------------- #
    st.subheader("Face Login")

    if st.button("Login with Face"):
        user_id = recognize_face()

        if user_id:
            user = get_user_by_id(user_id)
            if user:
                user_id = user[0]
                st.session_state["logged_in_user"] = user_id
                st.session_state["role"] = user[10]  # role index added
                role_display = {
                    "Customer": "Customer",
                    "Shopkeeper": "Shopkeeper",
                    "Government Officer": "Government Officer"
                }
                role_msg = role_display.get(user[10], user[10])
                
                # Log login (I - Logging & Monitoring)
                try:
                    log_login(user_id)
                except:
                    pass
                
                # Auto-redirect to appropriate dashboard
                if user[10] == "Customer":
                    st.session_state["page"] = "Customer Dashboard"
                elif user[10] == "Shopkeeper":
                    st.session_state["page"] = "Shopkeeper Dashboard"
                elif user[10] == "Government Officer":
                    st.session_state["page"] = "Government Dashboard"
                
                # Refresh the page to update sidebar and redirect
                safe_rerun()
            else:
                st.error("Face recognized but user not found. Please register.")
        else:
            st.error("Face not recognized. Try again or use Aadhaar login.")

    st.markdown("---")

    # --------------- FALLBACK LOGIN --------------- #
    st.subheader("Fallback Login (Aadhaar + Ration Card)")

    aadhaar = st.text_input("Aadhaar Number", key="aadhaar_login")
    ration_id = st.text_input("Ration Card Number", key="ration_login")

    if st.button("Login with Aadhaar"):
        if not aadhaar or not ration_id:
            st.error("Please enter both Aadhaar and Ration ID Number.")
            return

        user = get_user_by_aadhaar_ration(aadhaar, ration_id)

        if user:
            user_id = user[0]
            st.session_state["logged_in_user"] = user_id
            st.session_state["role"] = user[10]  # Save role in session
            role_display = {
                "Customer": "Customer",
                "Shopkeeper": "Shopkeeper",
                "Government Officer": "Government Officer"
            }
            role_msg = role_display.get(user[10], user[10])
            
            # Log login (I - Logging & Monitoring)
            try:
                log_login(user_id)
            except:
                pass
            
            # Auto-redirect to appropriate dashboard
            if user[10] == "Customer":
                st.session_state["page"] = "Customer Dashboard"
            elif user[10] == "Shopkeeper":
                st.session_state["page"] = "Shopkeeper Dashboard"
            elif user[10] == "Government Officer":
                st.session_state["page"] = "Government Dashboard"
            
            # Refresh the page to update sidebar and redirect
            safe_rerun()
        else:
            st.error("Invalid Aadhaar or Ration Card Number. Try Again.")

    # --------------- LOGOUT BUTTON --------------- #
    if "logged_in_user" in st.session_state:
        if st.button("Logout"):
            for key in ["logged_in_user", "role"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.warning("Logged out successfully!")
