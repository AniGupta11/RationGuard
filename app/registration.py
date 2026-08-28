import streamlit as st
import sqlite3
from app.utils.db_ops import (
    create_user,
    get_user_by_aadhaar_ration,
    delete_user,
)
from app.utils.face_recognition_module import (
    collect_face_samples,
    train_face_model,
    FaceDuplicateError,
    delete_user_faces,
)


def registration_page():
    st.title("User Registration")

    st.markdown("Fill all details to create a new RationGuard account.")

    with st.form("registration_form"):
        name = st.text_input("Full Name (Only letters, max 50 chars)")
        age = st.number_input("Age", min_value=1, max_value=129, step=1)
        gender = st.selectbox("Gender", ["Male", "Female", "Other"])

        role = st.selectbox(
            "Select Role",
            ["Customer", "Shopkeeper", "Govt"]
        )

        address = st.text_area("Address")

        aadhaar = st.text_input("Aadhaar Number (12 digits)")
        ration_id = st.text_input("Ration Card Number (10 digits)")
        income_level = st.selectbox(
            "Income Level",
            ["Low Income", "Middle Income", "High Income"],  # BPL removed
        )
        dependents = st.number_input(
            "Number of Dependents", min_value=0, max_value=5, step=1
        )

        dep_details = []
        if int(dependents) > 0:
            st.subheader("Dependent Details")
            for i in range(int(dependents)):
                cols = st.columns(3)
                with cols[0]:
                    st.text_input(f"Dependent Name #{i+1}", key=f"dep_name_{i}")
                with cols[1]:
                    st.selectbox(
                        f"Relation #{i+1}",
                        ["Child", "Spouse", "Parent", "Other"],
                        key=f"dep_rel_{i}"
                    )
                with cols[2]:
                    st.number_input(
                        f"Age #{i+1}", min_value=0, max_value=129, step=1, key=f"dep_age_{i}"
                    )
        phone = st.text_input("Phone Number (10 digits)")

        submit_btn = st.form_submit_button("Register and Capture Face")

    if submit_btn:
        # ---------------- VALIDATIONS ---------------- #

        # Name Validation
        if not name.replace(" ", "").isalpha() or len(name) > 50:
            st.error("Name must contain only alphabets and be max 50 characters long.")
            return

        # Aadhaar strict check
        if not (aadhaar.isdigit() and len(aadhaar) == 12 and not aadhaar.startswith("0")):
            st.error("Kindly enter the correct Aadhar ID (12 digits, cannot start with 0)")
            return

        # Ration ID strict check
        if not (ration_id.isdigit() and len(ration_id) == 10 and not ration_id.startswith("0")):
            st.error("Kindly enter the correct Ration Card Number (10 digits, cannot start with 0)")
            return

        # Phone strict check
        if not (phone.isdigit() and len(phone) == 10 and not phone.startswith("0")):
            st.error("Kindly enter a valid 10-digit Phone Number")
            return

        # Age validation (Stage-6)
        if age < 1 or age > 129:
            st.error("Age must be between 1 and 129.")
            return

        if dependents > 5:
            st.error("Dependents must be less than or equal to 5.")
            return

        valid_dependents = 0
        excluded = 0
        dep_rows = []
        if int(dependents) > 0:
            for i in range(int(dependents)):
                age_i = st.session_state.get(f"dep_age_{i}")
                name_i = st.session_state.get(f"dep_name_{i}")
                rel_i = st.session_state.get(f"dep_rel_{i}")
                if age_i is not None and int(age_i) >= 6:
                    valid_dependents += 1
                    dep_rows.append({"name": name_i or "", "relation": rel_i or "Other", "age": int(age_i)})
                else:
                    excluded += 1
            if excluded > 0:
                st.warning(f"{excluded} dependent(s) excluded due to age < 6.")

        # Role validation (Stage-6)
        if role not in ["Customer", "Shopkeeper", "Govt"]:
            st.error("Invalid role selected.")
            return

        # Prevent duplicate user
        existing = get_user_by_aadhaar_ration(aadhaar, ration_id)
        if existing:
            st.warning(
                f"User already exists with this Aadhaar and Ration ID. Welcome back, {existing[1]}."
            )
            return

        # ---------------- USER CREATION ---------------- #
        try:
            user_id = create_user(
                name=name,
                age=int(age),
                gender=gender,
                address=address,
                aadhaar=aadhaar,
                ration_id=ration_id,
                income_level=income_level,
                dependents=int(valid_dependents),
                phone=phone,
            )
        except Exception as e:
            st.error(f"Error while creating user: {e}")
            return

        try:
            if dep_rows:
                from app.utils.db_ops import save_dependents
                save_dependents(user_id, dep_rows)
        except Exception as e:
            st.warning(f"Dependent details could not be saved: {e}")

        # Save role and subsidy_eligible in DB (H - Database Enhancements)
        try:
            conn = sqlite3.connect("database/rationguard.db")
            cur = conn.cursor()
            db_role = "Government Officer" if role == "Govt" else role
            # Phase-8: All income levels are eligible for subsidy (with different percentages)
            # Low: 100%, Middle: 70%, High: 40%
            subsidy_eligible = 1  # All income levels eligible
            cur.execute("UPDATE users SET role = ?, subsidy_eligible = ? WHERE id = ?", 
                       (db_role, subsidy_eligible, user_id))
            conn.commit()
            conn.close()
        except Exception as e:
            st.error(f"Role and subsidy update failed: {e}")
            return
        
        # Phase-9: Create entitlements for Customer role
        if role == "Customer":
            try:
                from app.utils.entitlements import create_user_entitlements
                create_user_entitlements(user_id, int(valid_dependents), income_level)
                st.info("Monthly entitlements created successfully.")
            except Exception as e:
                st.warning(f"Entitlement creation failed: {e}")

        st.info(
            f"User created successfully with ID: {user_id}. "
            "Now we will capture your face for biometric authentication."
        )

        # ---------------- FACE CAPTURE ---------------- #
        try:
            collect_face_samples(user_id)
            st.success("Face images captured successfully.")
        except FaceDuplicateError as dup_err:
            delete_user_faces(user_id)
            delete_user(user_id)
            st.error(str(dup_err))
            st.warning("Registration cancelled because this face already exists in the system.")
            return
        except Exception as face_err:
            delete_user_faces(user_id)
            st.error(f"Face capture failed: {face_err}")
            return

        trained = train_face_model()
        if trained:
            st.success(f"Registration complete. Welcome, {name}.")
        else:
            st.warning("Face model could not be trained. Please try capturing again.")
