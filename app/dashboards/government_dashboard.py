import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from app.utils.db_ops import (
    get_all_bills,
    get_fraud_logs,
    get_total_beneficiaries,
    get_fraud_trend,
    get_commodity_stats,
    get_fraud_by_shopkeeper,
    get_connection
)
from app.utils.pricing import COMMODITY_INFO, COMMODITY_PRICES
from datetime import datetime, timedelta


def government_dashboard():
    st.title("Government Analytics & Reports")
    from app.utils.entitlements import ensure_all_customers_entitlements_current_month
    try:
        ensure_all_customers_entitlements_current_month()
    except:
        pass

    commodity_labels = [COMMODITY_INFO[key][0] for key in COMMODITY_INFO]

    user_id = st.session_state.get("logged_in_user")
    if not user_id:
        st.error("Please login to continue")
        st.stop()

    from app.utils.db_ops import get_user_by_id
    user = get_user_by_id(user_id)
    if not user:
        st.error("User not found. Please login again.")
        st.stop()
    
    # Role is at index 10: id, name, age, gender, address, aadhaar, ration_id, income_level, dependents, phone, role, created_at
    role = user[10] if len(user) > 10 else None
    role_str = str(role).strip() if role else None
    
    # Access control: Only Government Officer can access
    if role_str != "Government Officer":
        st.error(f"Access denied. Only Government Officers can access this dashboard. Your role: {role_str}")
        st.stop()

    # Total Beneficiaries (Stage-2)
    st.subheader("Total Beneficiaries")
    total_beneficiaries = get_total_beneficiaries()
    st.metric("Registered Customers", total_beneficiaries)

    st.markdown("---")

    st.subheader("Monthly Bills & Subsidy Trend")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT strftime('%Y-%m', timestamp) as month,
               COUNT(*) as bills,
               SUM(subsidy_availed) as subsidy
        FROM bills
        GROUP BY month
        ORDER BY month
    """)
    monthly = cur.fetchall()
    conn.close()
    if monthly:
        df_monthly = pd.DataFrame(monthly, columns=["Month", "Bills", "Subsidy"])
        col1, col2 = st.columns(2)
        with col1:
            fig_bills = px.line(df_monthly, x="Month", y="Bills", title="Monthly Bills")
            fig_bills.update_xaxes(type="category")
            st.plotly_chart(fig_bills, use_container_width=True)
        with col2:
            fig_subsidy = px.bar(df_monthly, x="Month", y="Subsidy", title="Monthly Subsidy Burden")
            fig_subsidy.update_xaxes(type="category")
            st.plotly_chart(fig_subsidy, use_container_width=True)

    st.markdown("---")
    st.subheader("Predictive Demand Forecast (Next 3 Months)")
    from app.utils.db_ops import get_all_monthly_usage_stats
    usage_stats = get_all_monthly_usage_stats()
    if usage_stats:
        df_usage = pd.DataFrame(usage_stats, columns=["Month", *commodity_labels, "TotalBills"])
        df_usage["TotalQuantity"] = df_usage[commodity_labels].sum(axis=1)
        df_usage_sorted = df_usage.sort_values("Month")
        df_usage_sorted["MonthLabel"] = df_usage_sorted["Month"].astype(str)
        last3 = df_usage_sorted["TotalQuantity"].tail(3)
        avg_last3 = (last3.mean() if not last3.empty else df_usage_sorted["TotalQuantity"].mean()) or 0
        if not df_usage_sorted.empty:
            last_month = pd.Period(str(df_usage_sorted["Month"].iloc[-1]), freq="M")
            forecast_months = [str((last_month + i).strftime("%Y-%m")) for i in range(1,4)]
        else:
            forecast_months = []
        if len(df_usage_sorted) >= 2:
            x = np.arange(len(df_usage_sorted))
            y = df_usage_sorted["TotalQuantity"].values
            slope, intercept = np.polyfit(x, y, 1)
            x_future = np.arange(len(df_usage_sorted), len(df_usage_sorted) + len(forecast_months))
            y_future = (slope * x_future + intercept).clip(min=0)
        else:
            y_future = np.full(len(forecast_months), avg_last3)
        df_forecast = pd.DataFrame({"MonthLabel": forecast_months, "ForecastQuantity": y_future})
        colf1, colf2 = st.columns(2)
        with colf1:
            fig_hist = px.line(df_usage_sorted, x="MonthLabel", y="TotalQuantity", title="Historical Total Demand")
            fig_hist.update_xaxes(type="category")
            st.plotly_chart(fig_hist, use_container_width=True)
        with colf2:
            fig_fc = px.line(df_forecast, x="MonthLabel", y="ForecastQuantity", title="Forecasted Total Demand")
            fig_fc.update_xaxes(type="category")
            st.plotly_chart(fig_fc, use_container_width=True)

    # Fraud Detection Trend (Daily/Monthly) (Stage-2)
    st.subheader("Fraud Detection Trend")
    
    trend_period = st.radio("Select Period", ["Daily (Last 30 days)", "Monthly (Last 12 months)"], horizontal=True)
    
    if "Daily" in trend_period:
        fraud_trend = get_fraud_trend(30)
        if fraud_trend:
            df_trend = pd.DataFrame(fraud_trend, columns=["Date", "Count"])
            df_trend["Date"] = pd.to_datetime(df_trend["Date"])
            fig = px.line(
                df_trend,
                x="Date",
                y="Count",
                title="Daily Fraud Detection Trend",
                markers=True
            )
            fig.update_xaxes(tickformat="%H:%M")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No fraud detected in the last 30 days")
    else:
        # Monthly trend
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT strftime('%Y-%m', timestamp) as month, COUNT(*) as count
            FROM fraud_logs
            WHERE timestamp >= datetime('now', '-12 months')
            GROUP BY month
            ORDER BY month DESC
        """)
        monthly_trend = cur.fetchall()
        conn.close()
        
        if monthly_trend:
            df_monthly = pd.DataFrame(monthly_trend, columns=["Month", "Count"])
            fig = px.bar(
                df_monthly,
                x="Month",
                y="Count",
                title="Monthly Fraud Detection Trend"
            )
            fig.update_xaxes(type="category")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No fraud detected in the last 12 months")

    st.markdown("---")

    # Total Ration Consumption Heatmap (C - Final Dashboards)
    st.subheader("Total Ration Consumption Heatmap")
    from app.utils.db_ops import get_all_monthly_usage_stats
    usage_stats = get_all_monthly_usage_stats()
    
    if usage_stats:
        # Create heatmap data for all 10 commodities
        months = [row[0] for row in usage_stats]
        commodity_names = commodity_labels
        
        # Build heatmap data
        heatmap_rows = []
        for month in months:
            for idx, name in enumerate(commodity_names):
                # Find the row for this month
                month_row = next((r for r in usage_stats if r[0] == month), None)
                if month_row:
                    quantity = month_row[idx + 1]  # +1 because index 0 is month_year
                    heatmap_rows.append({
                        "Month": month,
                        "Commodity": name,
                        "Quantity": quantity or 0
                    })
        
        df_heatmap = pd.DataFrame(heatmap_rows)
        
        if not df_heatmap.empty:
            # Create heatmap
            fig = px.density_heatmap(
                df_heatmap,
                x="Month",
                y="Commodity",
                z="Quantity",
                title="Total Ration Consumption Heatmap by Month (All 10 Commodities)",
                color_continuous_scale="YlOrRd"
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No consumption data available for heatmap")

    st.markdown("---")

    # Commodity Demand & Subsidy Stats (Stage-2, 10 Commodities)
    st.subheader("Commodity Demand & Subsidy Statistics")
    stats = get_commodity_stats()
    
    if stats and stats[11] > 0:  # total_bills > 0
        commodity_values = list(stats[: len(commodity_labels)])
        label_to_unit = {COMMODITY_INFO[key][0]: COMMODITY_INFO[key][1] for key in COMMODITY_INFO}
        cols = st.columns(5)

        for idx, (label, value) in enumerate(zip(commodity_labels, commodity_values)):
            col = cols[idx % len(cols)]
            unit = label_to_unit.get(label, "kg")
            with col:
                st.metric(f"Total {label}", f"{value:.0f} {unit}")

        with cols[-1]:
            st.metric("Total Subsidy", f"₹{stats[10]:.2f}")
            st.metric("Total Bills", f"{stats[11]}")

        commodity_data = {
            "Commodity": commodity_labels,
            "Quantity": commodity_values,
        }
        df_commodity = pd.DataFrame(commodity_data)
        fig = px.pie(
            df_commodity,
            values="Quantity",
            names="Commodity",
            title="Commodity Distribution (All 10 Commodities)"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No commodity statistics available")

    st.markdown("---")

    # Ranking: Most Fraud-Detected Shops (Stage-2)
    st.subheader("Most Fraud-Detected Shops Ranking")
    fraud_ranking = get_fraud_by_shopkeeper()
    
    if fraud_ranking:
        df_ranking = pd.DataFrame(fraud_ranking, columns=["Shopkeeper", "Fraud Count"])
        df_ranking = df_ranking.sort_values("Fraud Count", ascending=False)
        
        fig = px.bar(
            df_ranking,
            x="Shopkeeper",
            y="Fraud Count",
            title="Fraud Detection by Shopkeeper",
            color="Fraud Count",
            color_continuous_scale="Reds"
        )
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(df_ranking, use_container_width=True)
    else:
        st.success("✅ No fraud detected from any shopkeeper")

    st.markdown("---")

    # Phase-9: Income-wise Subsidy Breakdown Chart
    st.subheader("Income-wise Subsidy Breakdown")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT 
            users.income_level,
            COUNT(DISTINCT bills.user_id) as beneficiaries,
            SUM(bills.subsidy_availed) as total_subsidy,
            COUNT(bills.id) as total_bills
        FROM bills
        JOIN users ON bills.user_id = users.id
        WHERE users.role = 'Customer'
        GROUP BY users.income_level
    """)
    income_subsidy_data = cur.fetchall()
    conn.close()
    
    if income_subsidy_data:
        df_income = pd.DataFrame(income_subsidy_data, columns=["Income Level", "Beneficiaries", "Total Subsidy", "Bills"])
        df_income["Income Level"] = df_income["Income Level"].replace({"Below Poverty Line": "Low Income"})
        df_income = df_income.groupby("Income Level", as_index=False).agg({"Beneficiaries":"sum","Total Subsidy":"sum","Bills":"sum"})
        
        col1, col2 = st.columns(2)
        with col1:
            fig_subsidy = px.pie(
                df_income,
                values="Total Subsidy",
                names="Income Level",
                title="Subsidy Distribution by Income Level",
                color="Income Level",
                color_discrete_map={
                    "Low Income": "#ff6b6b",
                    "Middle Income": "#ffd93d",
                    "High Income": "#6bcf7f"
                }
            )
            st.plotly_chart(fig_subsidy, use_container_width=True)
        
        with col2:
            fig_beneficiaries = px.bar(
                df_income,
                x="Income Level",
                y="Beneficiaries",
                title="Beneficiaries by Income Level",
                color="Income Level",
                color_discrete_map={
                    "Low Income": "#ff6b6b",
                    "Middle Income": "#ffd93d",
                    "High Income": "#6bcf7f"
                }
            )
            st.plotly_chart(fig_beneficiaries, use_container_width=True)
        
        # Display table
        st.dataframe(df_income, use_container_width=True, hide_index=True)
    else:
        st.info("No subsidy data available for income-wise breakdown")

    st.markdown("---")

    # Phase-9: Family Size Statistics
    st.subheader("Family Size Distribution")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT 
            (dependents + 1) as family_size,
            COUNT(*) as households,
            AVG(bills.subsidy_availed) as avg_subsidy
        FROM users
        LEFT JOIN bills ON users.id = bills.user_id
        WHERE users.role = 'Customer'
        GROUP BY family_size
        ORDER BY family_size
    """)
    family_data = cur.fetchall()
    conn.close()
    
    if family_data:
        df_family = pd.DataFrame(family_data, columns=["Family Size", "Households", "Avg Subsidy"])
        
        col1, col2 = st.columns(2)
        with col1:
            fig_family = px.bar(
                df_family,
                x="Family Size",
                y="Households",
                title="Households by Family Size",
                color="Households",
                color_continuous_scale="Blues"
            )
            st.plotly_chart(fig_family, use_container_width=True)
        
        with col2:
            fig_avg_subsidy = px.line(
                df_family,
                x="Family Size",
                y="Avg Subsidy",
                title="Average Subsidy by Family Size",
                markers=True
            )
            st.plotly_chart(fig_avg_subsidy, use_container_width=True)
        
        # Display table
        st.dataframe(df_family, use_container_width=True, hide_index=True)
    else:
        st.info("No family size data available")

    st.markdown("---")

    # Policy Fairness Score (Stage-2)
    st.subheader("Policy Fairness Score")
    
    # Calculate fairness score based on subsidy distribution
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT 
            income_level,
            COUNT(*) as beneficiaries,
            SUM(subsidy_availed) as total_subsidy
        FROM users
        LEFT JOIN bills ON users.id = bills.user_id
        WHERE users.role = 'Customer'
        GROUP BY income_level
    """)
    fairness_data = cur.fetchall()
    conn.close()
    
    if fairness_data:
        df_fairness = pd.DataFrame(fairness_data, columns=["Income Level", "Beneficiaries", "Total Subsidy"])
        df_fairness["Income Level"] = df_fairness["Income Level"].replace({"Below Poverty Line": "Low Income"})
        df_fairness = df_fairness.groupby("Income Level", as_index=False).agg({"Beneficiaries":"sum","Total Subsidy":"sum"})
        
        # Calculate fairness score (subsidy should go to Low/Middle income)
        low_middle_subsidy = df_fairness[
            df_fairness["Income Level"].isin(["Low Income", "Middle Income"])
        ]["Total Subsidy"].sum() or 0
        total_subsidy = df_fairness["Total Subsidy"].sum() or 1
        
        fairness_score = (low_middle_subsidy / total_subsidy) * 100 if total_subsidy > 0 else 100
        
        st.metric("Policy Fairness Score", f"{fairness_score:.1f}%")
        
        if fairness_score >= 80:
            st.success("✅ Policy is fair - Subsidy is properly distributed")
        elif fairness_score >= 60:
            st.warning("⚠️ Policy needs improvement")
        else:
            st.error("❌ Policy fairness is low - Review required")
        
        # Display breakdown
        fig = px.bar(
            df_fairness,
            x="Income Level",
            y="Total Subsidy",
            title="Subsidy Distribution by Income Level",
            color="Income Level"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Insufficient data to calculate fairness score")

    st.markdown("---")

        # All Transactions Overview (Stage-2, 10 Commodities)
    st.subheader("All Transactions Overview")
    bills = get_all_bills()
    
    if bills:
        df_bills = pd.DataFrame(
            bills,
            columns=["Bill ID", "Customer", "Shopkeeper", "Date", *commodity_labels, "Total Amount", "Subsidy", "ML Score"],
        )
        
        # Create summary column
        df_bills["Commodities"] = df_bills.apply(
            lambda row: f"R:{row['Rice']:.1f} W:{row['Wheat']:.1f} S:{row['Sugar']:.1f} +7",
            axis=1
        )
        
        # Filters (Stage-5)
        col1, col2, col3 = st.columns(3)
        with col1:
            shop_options = ["All"] + sorted(df_bills["Shopkeeper"].dropna().unique().tolist())
            filter_shopkeeper = st.selectbox("Filter by Shopkeeper", options=shop_options, index=0)
        with col2:
            cust_options = ["All"] + sorted(df_bills["Customer"].dropna().unique().tolist())
            filter_customer = st.selectbox("Filter by Customer", options=cust_options, index=0)
        with col3:
            filter_date = st.date_input("Filter by Date", value=None)

        # Apply filters
        if filter_shopkeeper and filter_shopkeeper != "All":
            df_bills = df_bills[df_bills["Shopkeeper"] == filter_shopkeeper]
        if filter_customer and filter_customer != "All":
            df_bills = df_bills[df_bills["Customer"] == filter_customer]
        if filter_date:
            df_bills["Date"] = pd.to_datetime(df_bills["Date"])
            df_bills = df_bills[df_bills["Date"].dt.date == filter_date]

        # Keep original timestamp formatting
        
        # Display compact table
        display_cols = ["Bill ID", "Customer", "Shopkeeper", "Date", "Commodities", "Total Amount", "Subsidy", "ML Score"]
        st.dataframe(df_bills[display_cols], use_container_width=True, hide_index=True)
    else:
        st.info("No transactions recorded yet")

    st.markdown("---")

    # Top Fraud-Flagged Shops + Customers (C - Final Dashboards)
    st.subheader("Top Fraud-Flagged Shops & Customers")
    fraud_ranking = get_fraud_by_shopkeeper()
    
    if fraud_ranking:
        col1, col2 = st.columns(2)
        with col1:
            st.write("**Top Fraud-Flagged Shops:**")
            df_shops = pd.DataFrame(fraud_ranking[:10], columns=["Shopkeeper", "Fraud Count"])
            st.dataframe(df_shops, use_container_width=True, hide_index=True)
        
        with col2:
            # Top fraud customers
            fraud_logs = get_fraud_logs()
            if fraud_logs:
                from collections import Counter
                customer_fraud = Counter([log[1] for log in fraud_logs])
                top_customers = customer_fraud.most_common(10)
                df_customers = pd.DataFrame(top_customers, columns=["Customer", "Fraud Count"])
                st.write("**Top Fraud-Flagged Customers:**")
                st.dataframe(df_customers, use_container_width=True, hide_index=True)

    st.markdown("---")

    # Fraud Alerts & ML Detections (D - Alert System, 10 Commodities)
    st.subheader("Fraud Alerts & ML Detections")
    fraud_logs = get_fraud_logs()
    
    if fraud_logs:
        # Red notification banner (D - Alert System)
        st.error(f"🚨 **{len(fraud_logs)} FRAUD CASES DETECTED**")
        # Compact table with all 10 commodities and severity (Phase-8 K)
        df_fraud = pd.DataFrame(
            fraud_logs,
            columns=["ID", "Customer", "Date", "Reason", "ML Score", "Severity", *commodity_labels],
        )
        # Create summary column for better display
        df_fraud["Commodities"] = df_fraud.apply(
            lambda row: f"R:{row['Rice']:.1f} W:{row['Wheat']:.1f} S:{row['Sugar']:.1f} K:{row['Kerosene']:.1f} +6 more",
            axis=1
        )
        display_cols = ["ID", "Customer", "Date", "Severity", "Reason", "ML Score", "Commodities"]
        st.dataframe(df_fraud[display_cols], use_container_width=True, hide_index=True)
    else:
        st.success("✅ No fraud detected yet — System is running clean")
    
    st.markdown("---")
    
    # Subsidy Cost Impact Analysis (C - Final Dashboards, 10 Commodities)
    st.subheader("Subsidy Cost Impact Analysis")
    stats = get_commodity_stats()
    if stats:
        total_subsidy = float(stats[10] or 0)
        total_bills = int(stats[11] or 0)
        commodity_totals = [float(stats[idx] or 0) for idx, _ in enumerate(COMMODITY_INFO.keys())]
    else:
        total_subsidy = 0.0
        total_bills = 0
        commodity_totals = [0.0 for _ in COMMODITY_INFO.keys()]

    if total_subsidy > 0:
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Subsidy Cost", f"₹{total_subsidy:.2f}")
            st.info(f"Average subsidy per bill: ₹{(total_subsidy/total_bills):.2f}" if total_bills > 0 else "No bills")
        with col2:
            total_revenue = sum(
                commodity_totals[idx] * COMMODITY_PRICES[key]
                for idx, key in enumerate(COMMODITY_INFO.keys())
            )
            subsidy_percent = (total_subsidy / total_revenue * 100) if total_revenue > 0 else 0
            st.metric("Subsidy as % of Revenue", f"{subsidy_percent:.2f}%")
        df_rev = pd.DataFrame({
            "Commodity": commodity_labels,
            "Revenue": [
                commodity_totals[idx] * COMMODITY_PRICES[key]
                for idx, key in enumerate(COMMODITY_INFO.keys())
            ],
        })
        fig_rev = px.bar(df_rev.sort_values("Revenue", ascending=False), x="Commodity", y="Revenue", title="Commodity-wise Revenue")
        st.plotly_chart(fig_rev, use_container_width=True)
    
    st.markdown("---")
