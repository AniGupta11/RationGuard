import streamlit as st
import os
import pandas as pd
import plotly.express as px
from app.utils.db_ops import (
    get_user_by_id,
    get_user_bills,
    get_user_fraud_alerts
)
from app.utils.pricing import COMMODITY_LIMITS, COMMODITY_INFO


def customer_dashboard():
    st.title("Customer Dashboard")

    user_id = st.session_state.get("logged_in_user")
    if not user_id:
        st.error("Please login to continue")
        st.stop()

    user = get_user_by_id(user_id)
    if not user:
        st.error("User not found")
        st.stop()
    
    # Role is at index 10: id, name, age, gender, address, aadhaar, ration_id, income_level, dependents, phone, role, created_at
    role = user[10] if len(user) > 10 else None
    role_str = str(role).strip() if role else None
    
    # Access control: Only Customer and Government Officer can access
    if role_str not in ["Customer", "Government Officer"]:
        st.error(f"Access denied. Only Customers and Government Officers can access this dashboard. Your role: {role_str}")
        st.stop()

    # Profile Box (C - Final Dashboards: Name, Aadhar, Role)
    st.subheader("Profile")
    with st.container():
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.info(f"**Name:** {user[1]}")
        with col2:
            st.info(f"**Aadhaar:** {user[5]}")
        with col3:
            st.info(f"**Role:** {role_str}")
        with col4:
            # Phase-9: Total savings calculation
            bills = get_user_bills(user_id)
            if bills:
                total_subsidy = sum(bill[13] for bill in bills)  # subsidy_availed column
                st.success(f"**Total Savings:** ₹{total_subsidy:.2f}")
            else:
                st.info(f"**Total Savings:** ₹0.00")

    st.markdown("---")

    # Ration Limit vs Consumption (C - Final Dashboards, 10 Commodities)
    st.subheader("Ration Limit vs Consumption")
    bills = get_user_bills(user_id)
    
    # Phase-9: Use entitlement-based limits instead of fixed COMMODITY_LIMITS
    from app.utils.entitlements import get_user_entitlements, get_remaining_quota
    from datetime import datetime
    current_month = datetime.now().strftime('%Y-%m')
    entitlements = get_user_entitlements(user_id, current_month)
    entitlement_dict = {row[0]: row[1] for row in entitlements} if entitlements else {}
    remaining = get_remaining_quota(user_id, current_month)
    
    commodity_keys = list(COMMODITY_INFO.keys())
    commodity_labels = [COMMODITY_INFO[key][0] for key in commodity_keys]

    if bills:
        # Calculate monthly totals for all 10 commodities
        df_bills = pd.DataFrame(
            bills,
            columns=["Bill ID", "Date", *commodity_labels, "Total Amount", "Subsidy", "PDF", "ML Score", "Shopkeeper"],
        )
        df_bills["Date"] = pd.to_datetime(df_bills["Date"])
        
        # Current month bills
        current_month_period = pd.Timestamp.now().to_period('M')
        monthly_bills = df_bills[df_bills["Date"].dt.to_period('M') == current_month_period]
        
        if not monthly_bills.empty or entitlement_dict:
            # Calculate totals for all commodities
            commodity_totals = {
                key: (monthly_bills[label].sum() if not monthly_bills.empty else 0)
                for key, label in zip(commodity_keys, commodity_labels)
            }
            
            # Display in 2 rows of 5 columns (G - UI/UX: Compact tables & cards)
            commodity_display = {
                key: (COMMODITY_INFO[key][0], COMMODITY_INFO[key][1]) for key in commodity_keys
            }
            
            # Row 1
            cols1 = st.columns(5)
            commodities_list = list(commodity_display.items())
            for idx, (key, (name, unit)) in enumerate(commodities_list[:5]):
                with cols1[idx]:
                    # Use entitlement-based limit if available, otherwise fallback to COMMODITY_LIMITS
                    limit = entitlement_dict.get(key, COMMODITY_LIMITS.get(key, 0))
                    total = commodity_totals.get(key, 0)
                    remaining_qty = remaining.get(key, 0)
                    percent = (total / limit * 100) if limit > 0 else 0
                    st.metric(name, f"{total:.1f}/{limit:.1f} {unit}", f"Remaining: {remaining_qty:.1f}")
                    st.progress(min(percent / 100, 1.0))
            
            # Row 2
            cols2 = st.columns(5)
            for idx, (key, (name, unit)) in enumerate(commodities_list[5:]):
                with cols2[idx]:
                    # Use entitlement-based limit if available, otherwise fallback to COMMODITY_LIMITS
                    limit = entitlement_dict.get(key, COMMODITY_LIMITS.get(key, 0))
                    total = commodity_totals.get(key, 0)
                    remaining_qty = remaining.get(key, 0)
                    percent = (total / limit * 100) if limit > 0 else 0
                    st.metric(name, f"{total:.1f}/{limit:.1f} {unit}", f"Remaining: {remaining_qty:.1f}")
                    st.progress(min(percent / 100, 1.0))
        else:
            st.info("No transactions this month")
    else:
        st.info("No transactions found yet")

    st.markdown("---")

    # View All Bills with PDF Download (C - Final Dashboards: PDF download, 10 Commodities)
    st.subheader("All Bills")
    if bills:
        # Compact table (G - UI/UX: Compact tables & cards)
        df_bills = pd.DataFrame(
            bills,
            columns=["Bill ID", "Date", *commodity_labels, "Total Amount", "Subsidy", "PDF Path", "ML Score", "Shopkeeper"],
        )
        
        # Create summary columns for display
        df_bills["Commodities"] = df_bills.apply(
            lambda row: f"R:{row['Rice']:.1f} W:{row['Wheat']:.1f} S:{row['Sugar']:.1f} +7 more",
            axis=1,
        )
        
        # Display compact table with key info
        display_cols = ["Bill ID", "Date", "Commodities", "Total Amount", "Subsidy", "Shopkeeper"]
        st.dataframe(
            df_bills[display_cols],
            use_container_width=True,
            hide_index=True
        )
        
        # PDF Download section
        st.markdown("### 📥 Download Bill PDFs")
        bill_options = {f"Bill #{bill[0]} - {bill[1]}": bill for bill in bills}
        selected_bill_key = st.selectbox("Select Bill to Download", list(bill_options.keys()))
        
        if selected_bill_key:
            selected_bill = bill_options[selected_bill_key]
            pdf_path = selected_bill[14]  # file_path column (index 14 in new schema)
            
            if pdf_path and os.path.exists(pdf_path):
                with open(pdf_path, "rb") as pdf_file:
                    st.download_button(
                        label="📄 Download Bill PDF",
                        data=pdf_file.read(),
                        file_name=f"bill_{selected_bill[0]}.pdf",
                        mime="application/pdf"
                    )
            else:
                st.warning("PDF file not available for this bill.")
    else:
        st.info("No bills available")

    st.markdown("---")

    # Recent Fraud Alerts (C - Final Dashboards, D - Alert System)
    st.subheader("Recent Fraud Alerts")
    fraud_alerts = get_user_fraud_alerts(user_id)
    
    if fraud_alerts:
        # Red notification banner (D - Alert System)
        st.error("🚨 **FRAUD ALERTS DETECTED**")
        
        # Alert table in dashboard (D - Alert System, G - UI/UX: Compact tables)
        df_alerts = pd.DataFrame(fraud_alerts, columns=["ID", "Timestamp", "Reason", "ML Score"])
        st.dataframe(df_alerts, use_container_width=True, hide_index=True)
        
        # Expandable details
        for alert in fraud_alerts:
            with st.expander(f"🔍 Alert #{alert[0]} - {alert[1]}"):
                st.write(f"**Reason:** {alert[2]}")
                st.write(f"**ML Score:** {alert[3]:.2f}" if alert[3] else "**ML Score:** N/A")
    else:
        st.success("✅ No fraud alerts - Your account is clean")

    st.markdown("---")

    # Monthly Expense Chart (Stage-2, 10 Commodities)
    st.subheader("Monthly Expense Chart")
    if bills:
        df_bills = pd.DataFrame(
            bills,
            columns=["Bill ID", "Date", *commodity_labels, "Total Amount", "Subsidy", "PDF", "ML Score", "Shopkeeper"],
        )
        df_bills["Date"] = pd.to_datetime(df_bills["Date"])
        df_bills["Month"] = df_bills["Date"].dt.to_period('M').astype(str)
        
        monthly_expenses = df_bills.groupby("Month")["Total Amount"].sum().reset_index()
        
        fig = px.bar(
            monthly_expenses, 
            x="Month", 
            y="Total Amount",
            title="Monthly Expenses",
            labels={"Total Amount": "Amount (₹)", "Month": "Month"}
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No expense data available")
