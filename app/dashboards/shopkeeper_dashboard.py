import streamlit as st
import os
import pandas as pd
import plotly.express as px
from app.utils.db_ops import (
    get_user_by_id,
    get_shopkeeper_bills,
    get_fraud_logs,
    get_connection,
    get_shop_stock,
    get_users_by_role
)
from app.utils.streamlit_helpers import safe_rerun
from datetime import datetime, timedelta
from app.utils.pricing import COMMODITY_PRICES, COMMODITY_INFO


def shopkeeper_dashboard():
    st.title("Shopkeeper Dashboard")

    user_id = st.session_state.get("logged_in_user")
    if not user_id:
        st.error("Please login to continue")
        st.stop()

    user = get_user_by_id(user_id)
    if not user:
        st.error("User not found. Please login again.")
        st.stop()
    
    # Role is at index 10: id, name, age, gender, address, aadhaar, ration_id, income_level, dependents, phone, role, created_at
    role = user[10] if len(user) > 10 else None
    role_str = str(role).strip() if role else None
    
    # Access control: Only Shopkeeper and Government Officer can access
    if role_str not in ["Shopkeeper", "Government Officer"]:
        st.error(f"Access denied. Only Shopkeepers and Government Officers can access this dashboard. Your role: {role_str}")
        st.stop()

    target_shopkeeper_id = user_id
    target_shopkeeper_name = user[1]
    if role_str == "Government Officer":
        shopkeeper_rows = get_users_by_role("Shopkeeper")
        if not shopkeeper_rows:
            st.info("No shopkeepers available to review.")
            st.stop()
        options = [f"{name} (ID #{uid})" for uid, name in shopkeeper_rows]
        selected_label = st.selectbox(
            "Select shopkeeper to analyze",
            options,
            key="gov_shopkeeper_picker"
        )
        selected_index = options.index(selected_label)
        target_shopkeeper_id = shopkeeper_rows[selected_index][0]
        target_shopkeeper = get_user_by_id(target_shopkeeper_id)
        if not target_shopkeeper:
            st.error("Unable to load selected shopkeeper. Please refresh.")
            st.stop()
        target_shopkeeper_name = target_shopkeeper[1]
        st.success(f"Government mode: analyzing shopkeeper **{target_shopkeeper_name}** (ID #{target_shopkeeper_id})")
    else:
        st.info("Shopkeeper mode: displaying your business metrics.")

    # Pending & Recent Customers Served (Stage-2)
    st.subheader("Recent Customers Served")
    bills = get_shopkeeper_bills(target_shopkeeper_id)
    commodity_keys = list(COMMODITY_INFO.keys())
    commodity_labels = [COMMODITY_INFO[key][0] for key in commodity_keys]
    
    if bills:
        # Today's transactions
        today = datetime.now().date()
        today_bills = [b for b in bills if datetime.strptime(b[2], "%Y-%m-%d %H:%M:%S").date() == today]
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Today's Transactions", len(today_bills))
        with col2:
            today_revenue = sum(b[13] for b in today_bills)  # total_amount column (index 13 in new schema)
            st.metric("Today's Revenue", f"₹{today_revenue:.2f}")
        
        # Recent customers table (10 Commodities)
        if bills:
            df_recent = pd.DataFrame(
                bills[:10],
                columns=["Bill ID", "Customer", "Date", *commodity_labels, "Total Amount", "Subsidy", "ML Score"],
            )
            # Create summary column
            df_recent["Items"] = df_recent.apply(
                lambda row: f"R:{row['Rice']:.1f} W:{row['Wheat']:.1f} S:{row['Sugar']:.1f} +7",
                axis=1
            )
            st.dataframe(
                df_recent[["Bill ID", "Customer", "Date", "Items", "Total Amount", "Subsidy"]],
                use_container_width=True,
                hide_index=True
            )
    else:
        st.info("No transactions recorded yet")

    st.markdown("---")

    # Daily Transactions & Revenue (Stage-2, 10 Commodities)
    st.subheader("Daily Transactions & Revenue")
    if bills:
        df_bills = pd.DataFrame(
            bills,
            columns=["Bill ID", "Customer", "Date", *commodity_labels, "Total Amount", "Subsidy", "ML Score"],
        )
        df_bills["Date"] = pd.to_datetime(df_bills["Date"])
        df_bills["Day"] = df_bills["Date"].dt.date
        
        daily_stats = df_bills.groupby("Day").agg({
            "Bill ID": "count",
            "Total Amount": "sum",
            "Subsidy": "sum"
        }).reset_index()
        daily_stats.columns = ["Date", "Transactions", "Revenue", "Subsidy"]
        
        col1, col2 = st.columns(2)
        with col1:
            fig1 = px.bar(
                daily_stats,
                x="Date",
                y="Transactions",
                title="Daily Transactions"
            )
            st.plotly_chart(fig1, use_container_width=True)
        
        with col2:
            daily_melt = daily_stats.melt(id_vars="Date", value_vars=["Revenue", "Subsidy"], var_name="Metric", value_name="Amount")
            fig2 = px.line(
                daily_melt,
                x="Date",
                y="Amount",
                color="Metric",
                markers=True,
                title="Revenue vs Subsidy Trend"
            )
            st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("No transaction data available")

    st.markdown("---")

    st.subheader("Top Commodities Sold")
    if bills:
        df_bills = pd.DataFrame(
            bills,
            columns=["Bill ID", "Customer", "Date", *commodity_labels, "Total Amount", "Subsidy", "ML Score"],
        )
        totals = {
            label: df_bills[label].sum()
            for label in commodity_labels
        }
        df_totals = pd.DataFrame({"Commodity": list(totals.keys()), "Quantity": list(totals.values())})
        fig_top = px.bar(df_totals.sort_values("Quantity", ascending=False), x="Commodity", y="Quantity", title="Commodities by Quantity")
        st.plotly_chart(fig_top, use_container_width=True)

    st.markdown("---")
    st.subheader("Revenue by Commodity")
    if bills:
        df_bills = pd.DataFrame(
            bills,
            columns=["Bill ID", "Customer", "Date", *commodity_labels, "Total Amount", "Subsidy", "ML Score"],
        )
        revenue = {
            COMMODITY_INFO[key][0]: df_bills[COMMODITY_INFO[key][0]].sum() * COMMODITY_PRICES[key]
            for key in commodity_keys
        }
        df_rev = pd.DataFrame({"Commodity": list(revenue.keys()), "Revenue": list(revenue.values())})
        fig_rev = px.bar(df_rev.sort_values("Revenue", ascending=False), x="Commodity", y="Revenue", title="Revenue by Commodity")
        st.plotly_chart(fig_rev, use_container_width=True)

    st.markdown("---")
    st.subheader("Top Customers by Revenue")
    if bills:
        df_bills = pd.DataFrame(
            bills,
            columns=["Bill ID", "Customer", "Date", *commodity_labels, "Total Amount", "Subsidy", "ML Score"],
        )
        top_customers = df_bills.groupby("Customer")["Total Amount"].sum().sort_values(ascending=False).head(7)
        df_top_cust = top_customers.reset_index().rename(columns={"Total Amount": "Revenue"})
        fig_customers = px.bar(
            df_top_cust,
            x="Revenue",
            y="Customer",
            orientation="h",
            title="Highest Spending Customers",
            labels={"Revenue": "Revenue (₹)"}
        )
        st.plotly_chart(fig_customers, use_container_width=True)
        st.dataframe(df_top_cust, use_container_width=True, hide_index=True)
    else:
        st.info("No customer revenue data available yet.")

    # Generate Bill Button → Billing Page (Stage-2)
    if role_str == "Shopkeeper":
        st.subheader("Quick Actions")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Generate New Bill", type="primary"):
                st.session_state["page"] = "Billing"
                safe_rerun()
        with col2:
            # Export Daily Report PDF (Stage-3)
            if st.button("Export Daily Report PDF"):
                from app.utils.reports import generate_shopkeeper_daily_report
                report_path = generate_shopkeeper_daily_report(target_shopkeeper_id, target_shopkeeper_name)
                if report_path and os.path.exists(report_path):
                    with open(report_path, "rb") as pdf_file:
                        st.download_button(
                            label="Download Daily Report",
                            data=pdf_file.read(),
                            file_name=f"daily_report_{datetime.now().strftime('%Y%m%d')}.pdf",
                            mime="application/pdf"
                        )
                else:
                    st.info("No transactions today to generate report.")
    else:
        st.info("Government mode: billing actions are disabled (read-only view).")

    st.markdown("---")

    # Stock Monitoring
    st.subheader("Stock Monitoring")
    try:
        stock_rows = get_shop_stock(target_shopkeeper_id)
        if stock_rows:
            df_stock = pd.DataFrame(stock_rows, columns=["Commodity", "Allocated", "Used", "Month"])
            df_stock["Remaining"] = df_stock["Allocated"] - df_stock["Used"]
            st.dataframe(df_stock[["Commodity","Allocated","Used","Remaining"]], use_container_width=True, hide_index=True)
            low = df_stock[df_stock["Remaining"] <= df_stock["Allocated"]*0.3]
            if not low.empty:
                st.warning("Low stock alerts:")
                for _, r in low.iterrows():
                    st.write(f"• {r['Commodity']}: {r['Remaining']:.1f} left")
        else:
            st.info("No stock data available")
    except Exception:
        st.info("Stock monitoring not configured")

    st.markdown("---")

    # Fraud Attempts Overview (Stage-2, Stage-4)
    st.subheader("Fraud Attempts Overview")
    
    # Get fraud logs related to this shopkeeper's bills
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT fraud_logs.id, users.name, fraud_logs.timestamp, 
               fraud_logs.reason, fraud_logs.ml_score
        FROM fraud_logs
        JOIN bills ON fraud_logs.user_id = bills.user_id
        JOIN users ON fraud_logs.user_id = users.id
        WHERE bills.shopkeeper_id = ?
        ORDER BY fraud_logs.timestamp DESC
        LIMIT 20
    """, (target_shopkeeper_id,))
    fraud_attempts = cur.fetchall()
    conn.close()
    
    if fraud_attempts:
        st.warning(f"⚠️ {len(fraud_attempts)} fraud attempts detected in your transactions")
        df_fraud = pd.DataFrame(fraud_attempts, columns=[
            "ID", "Customer", "Date", "Reason", "ML Score"
        ])
        st.dataframe(df_fraud, use_container_width=True)
    else:
        st.success("✅ No fraud attempts detected - All transactions are clean")
