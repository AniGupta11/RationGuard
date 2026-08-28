import streamlit as st
import os
import json
from app.utils.db_ops import (
    get_user_by_id,
    save_bill,
    get_user_bills,
    get_connection,
    log_fraud,
    get_shopkeeper_bills
)
from app.utils.fraud_predictor import ml_model_predict_fraud
from app.utils.fraud_rules import rule_based_fraud_check
from app.utils.file_manager import generate_bill_pdf
from app.utils.pricing import calculate_bill, COMMODITY_INFO
from app.utils.streamlit_helpers import safe_rerun

# NEW WHATSAPP SERVICE IMPORT
from app.notifications.whatsapp_service import send_whatsapp_alert

COMMODITY_LABELS = {
    key: f"{name} ({unit})" for key, (name, unit) in COMMODITY_INFO.items()
}


def calculate_subsidy(income_level, total_amount):
    if income_level == "Low Income":
        subsidy = total_amount * 1.0
    elif income_level == "Middle Income":
        subsidy = total_amount * 0.70
    elif income_level == "High Income":
        subsidy = total_amount * 0.40
    else:
        subsidy = 0.0
    return subsidy


def billing_page():
    user_id = st.session_state.get("logged_in_user", None)
    if not user_id:
        st.error("Please login first.")
        return

    user = get_user_by_id(user_id)
    if not user:
        st.error("User not found. Please login again.")
        return

    role = user[10] if len(user) > 10 else None
    role_str = str(role).strip() if role else None

    if role_str not in ["Customer", "Shopkeeper", "Government Officer"]:
        st.error(f"Access denied. Billing available only for valid roles. Your role: {role_str}")
        return

    st.title("Billing System")

    if role_str == "Customer":
        customer_aadhaar = user[5]
        st.info(f"Aadhaar: {customer_aadhaar}")
    else:
        customer_aadhaar = st.text_input("Enter Customer Aadhaar Number")

    # ENTITLEMENT + QUOTA (no changes)
    if customer_aadhaar and customer_aadhaar.isdigit() and len(customer_aadhaar) == 12:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, name, dependents, income_level FROM users WHERE aadhaar = ?", (customer_aadhaar,))
        preview_customer = cur.fetchone()
        conn.close()
        if preview_customer:
            from app.utils.entitlements import ensure_user_entitlements_current_month, get_remaining_quota
            ensure_user_entitlements_current_month(preview_customer[0])
            remaining = get_remaining_quota(preview_customer[0])

            st.info(f"Customer: {preview_customer[1]} | Family Size: {preview_customer[2] + 1} | Income: {preview_customer[3]}")
            # your metrics UI untouched

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        rice = st.number_input(COMMODITY_LABELS["rice"], min_value=0, max_value=50, value=0)
        wheat = st.number_input(COMMODITY_LABELS["wheat"], min_value=0, max_value=50, value=0)
        sugar = st.number_input(COMMODITY_LABELS["sugar"], min_value=0, max_value=50, value=0)
    with col2:
        kerosene = st.number_input(COMMODITY_LABELS["kerosene"], min_value=0, max_value=50, value=0)
        salt = st.number_input(COMMODITY_LABELS["salt"], min_value=0, max_value=50, value=0)
        soyabeanoil = st.number_input(COMMODITY_LABELS["soyabeanoil"], min_value=0, max_value=50, value=0)
    with col3:
        palmoil = st.number_input(COMMODITY_LABELS["palmoil"], min_value=0, max_value=50, value=0)
        masoor = st.number_input(COMMODITY_LABELS["masoor"], min_value=0, max_value=50, value=0)
        moong = st.number_input(COMMODITY_LABELS["moong"], min_value=0, max_value=50, value=0)
    with col4:
        chana = st.number_input(COMMODITY_LABELS["chana"], min_value=0, max_value=50, value=0)

    if st.button("Generate Bill"):
        if not customer_aadhaar or len(customer_aadhaar) != 12 or not customer_aadhaar.isdigit():
            st.error("Invalid Aadhaar number.")
            return

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""SELECT id, name, age, gender, address, aadhaar,
            ration_id, income_level, dependents, phone, role, created_at
            FROM users WHERE aadhaar = ?""", (customer_aadhaar,))
        customer = cur.fetchone()
        conn.close()

        if not customer:
            st.error("Customer not found")
            return

        customer_id = customer[0]
        customer_name = customer[1]
        customer_income = customer[7]
        customer_phone = "+91" + customer[9]  # NEW: DYNAMIC CUSTOMER PHONE

        commodities_dict = {
            "rice": rice,
            "wheat": wheat,
            "sugar": sugar,
            "kerosene": kerosene,
            "salt": salt,
            "soyabeanoil": soyabeanoil,
            "palmoil": palmoil,
            "masoor": masoor,
            "moong": moong,
            "chana": chana,
        }

        # ENTITLEMENT, FRAUD, OVERRIDE BLOCKS — ALL KEPT SAME
        from app.utils.entitlements import get_remaining_quota
        remaining = get_remaining_quota(customer_id)
        entitlement_violations = []
        for c, q in commodities_dict.items():
            if q > remaining.get(c, 0):
                label = COMMODITY_LABELS.get(c, c.title())
                entitlement_violations.append(f"{label} exceeds entitlement")
        if entitlement_violations:
            st.error("Entitlement exceeded — Blocked")
            return

        total_amount = calculate_bill(**commodities_dict)
        subsidy_availed = calculate_subsidy(customer_income, total_amount)
        final_amount = total_amount - subsidy_availed

        st.subheader("Bill Summary")
        s1, s2, s3 = st.columns(3)
        with s1:
            st.metric("Total Amount", f"₹{total_amount:.2f}")
        with s2:
            st.metric("Subsidy Provided", f"₹{subsidy_availed:.2f}")
        with s3:
            st.metric("Amount After Subsidy", f"₹{final_amount:.2f}")

        rule_alerts, fraud_severity = ru
        le_based_fraud_check(customer, commodities_dict, user_id)
        ml_is_fraud, ml_score = ml_model_predict_fraud(customer, commodities_dict)
        is_fraud = ml_is_fraud or len(rule_alerts) > 0
        fraud_reason = "; ".join(rule_alerts)

        if is_fraud:
            log_fraud(customer_id, fraud_reason, ml_score, commodities_dict, fraud_severity)
            st.error("Fraud Detected")

            #  WhatsApp Fraud Alert — ADDED HERE
            send_whatsapp_alert(customer_phone, f"🚨 FRAUD BLOCKED — Check ration usage.\nReason: {fraud_reason}")

            if not st.session_state.get("fraud_override"):
                if st.button("Override"):
                    st.session_state["fraud_override"] = True
                    safe_rerun()
                return
            st.warning("Override used — Fraud logged")
            st.session_state["fraud_override"] = False

        pdf_path = generate_bill_pdf(customer_name, commodities_dict, final_amount)

        bill_id = save_bill(
            user_id=customer_id,
            shopkeeper_id=user_id,
            commodities_dict=commodities_dict,
            total_amount=final_amount,
            file_path=pdf_path,
            subsidy_availed=subsidy_availed,
            subsidy_eligible=True,
            ml_score=ml_score,
            commodity_qty=json.dumps(commodities_dict)
        )

        st.success(f"Bill ID: {bill_id}")
        st.info(f"Total: ₹{total_amount:.2f} | Subsidy: ₹{subsidy_availed:.2f} | Payable: ₹{final_amount:.2f}")

        #  WhatsApp Bill Success Alert — ADDED HERE
        send_whatsapp_alert(customer_phone, f"Bill Success ₹{final_amount:.2f}\nThank you for using RationGuard!")

def bill_history_page():
    user_id = st.session_state.get("logged_in_user", None)
    if not user_id:
        st.error("Please login first.")
        return

    user = get_user_by_id(user_id)
    if not user:
        st.error("User not found. Please login again.")
        return

    role = user[10] if len(user) > 10 else None
    role_str = str(role).strip() if role else None

    st.title("Bill History")

    commodity_keys = list(COMMODITY_INFO.keys())
    commodity_labels = [COMMODITY_INFO[key][0] for key in commodity_keys]

    if role_str == "Customer":
        bills = get_user_bills(user_id)
        if bills:
            import pandas as pd
            df_bills = pd.DataFrame(
                bills,
                columns=[
                    "Bill ID",
                    "Date",
                    *commodity_labels,
                    "Total Amount",
                    "Subsidy",
                    "PDF",
                    "ML Score",
                    "Shopkeeper",
                ],
            )
            st.dataframe(df_bills.drop(columns=["PDF"]), use_container_width=True, hide_index=True)

            st.markdown("### Download Bill PDFs")
            options = {f"Bill #{row[0]} - {row[1]}": row for row in bills}
            selected_key = st.selectbox("Select Bill", list(options.keys()))
            if selected_key:
                selected = options[selected_key]
                pdf_path = selected[14]
                if pdf_path and os.path.exists(pdf_path):
                    with open(pdf_path, "rb") as f:
                        st.download_button(
                            label="Download PDF",
                            data=f.read(),
                            file_name=f"bill_{selected[0]}.pdf",
                            mime="application/pdf",
                        )
                else:
                    st.warning("PDF file not available for this bill.")
        else:
            st.info("No bills available")
    elif role_str == "Shopkeeper":
        bills = get_shopkeeper_bills(user_id)
        if bills:
            import pandas as pd
            df_bills = pd.DataFrame(
                bills,
                columns=[
                    "Bill ID",
                    "Customer",
                    "Date",
                    *commodity_labels,
                    "Total Amount",
                    "Subsidy",
                    "ML Score",
                ],
            )
            st.dataframe(df_bills, use_container_width=True, hide_index=True)
        else:
            st.info("No bills available")
    else:
        st.info("Use dashboards to review bills and analytics.")
