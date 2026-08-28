import os
from fpdf import FPDF
from datetime import datetime
import pandas as pd
from app.utils.db_ops import (
    get_shopkeeper_bills,
    get_all_bills,
    get_fraud_logs,
    get_commodity_stats,
    get_fraud_by_shopkeeper
)
from app.utils.pricing import COMMODITY_INFO


class PDFReport(FPDF):
    def header(self):
        self.set_font("Arial", "B", 16)
        self.cell(0, 10, "RationGuard AI - Report", 0, 1, "C")
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.cell(0, 10, f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 0, 0, "C")


def generate_shopkeeper_daily_report(shopkeeper_id, shopkeeper_name):
    """Generate daily report PDF for Shopkeeper (Stage-3)"""
    bills = get_shopkeeper_bills(shopkeeper_id)
    
    if not bills:
        return None
    
    # Filter today's bills
    today = datetime.now().date()
    today_bills = [
        b for b in bills 
        if datetime.strptime(b[2], "%Y-%m-%d %H:%M:%S").date() == today
    ]
    
    pdf = PDFReport()
    pdf.add_page()
    
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, f"Daily Report - {shopkeeper_name}", 0, 1, "C")
    pdf.ln(5)
    
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 10, f"Date: {today.strftime('%Y-%m-%d')}", 0, 1)
    pdf.ln(5)
    
    # Summary (10 Commodities)
    total_transactions = len(today_bills)
    total_revenue = sum(b[13] for b in today_bills)  # total_amount (index 13 in new schema)
    
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Summary", 0, 1)
    pdf.set_font("Arial", size=10)
    pdf.cell(0, 8, f"Total Transactions: {total_transactions}", 0, 1)
    pdf.cell(0, 8, f"Total Revenue: ₹{total_revenue:.2f}", 0, 1)
    pdf.ln(5)
    
    # Transactions table
    if today_bills:
        pdf.set_font("Arial", "B", 10)
        pdf.cell(40, 8, "Customer", 1, 0)
        pdf.cell(30, 8, "Amount", 1, 0)
        pdf.cell(30, 8, "Subsidy", 1, 1)
        
        pdf.set_font("Arial", size=9)
        for bill in today_bills:
            pdf.cell(40, 8, bill[1][:30], 1, 0)  # customer name
            pdf.cell(30, 8, f"₹{bill[13]:.2f}", 1, 0)  # amount (index 13)
            pdf.cell(30, 8, f"₹{bill[14]:.2f}", 1, 1)  # subsidy (index 14)
    
    # Save PDF
    report_dir = "pdf_reports"
    if not os.path.exists(report_dir):
        os.makedirs(report_dir)
    
    filename = f"shopkeeper_report_{shopkeeper_id}_{today.strftime('%Y%m%d')}.pdf"
    file_path = os.path.join(report_dir, filename)
    pdf.output(file_path)
    
    return file_path


def generate_government_analytics_report():
    """Generate fairness + fraud analytics PDF for Government (Stage-3)"""
    pdf = PDFReport()
    pdf.add_page()
    
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Government Analytics & Fraud Report", 0, 1, "C")
    pdf.ln(5)
    
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 10, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 0, 1)
    pdf.ln(5)
    
    # Commodity Statistics (10 Commodities)
    stats = get_commodity_stats()
    if stats:
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "Commodity Distribution Statistics (All 10 Commodities)", 0, 1)
        pdf.set_font("Arial", size=10)
        commodity_labels = [COMMODITY_INFO[key][0] for key in COMMODITY_INFO]
        units = {COMMODITY_INFO[key][0]: COMMODITY_INFO[key][1] for key in COMMODITY_INFO}
        for idx, label in enumerate(commodity_labels):
            unit = units.get(label, "kg")
            pdf.cell(0, 8, f"Total {label} Distributed: {stats[idx]:.0f} {unit}", 0, 1)
        pdf.cell(0, 8, f"Total Subsidy Provided: ₹{stats[10]:.2f}", 0, 1)
        pdf.cell(0, 8, f"Total Bills: {stats[11]}", 0, 1)
        pdf.ln(5)
    
    # Fraud Detection Ranking
    fraud_ranking = get_fraud_by_shopkeeper()
    if fraud_ranking:
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "Fraud Detection by Shopkeeper", 0, 1)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(80, 8, "Shopkeeper", 1, 0)
        pdf.cell(40, 8, "Fraud Count", 1, 1)
        
        pdf.set_font("Arial", size=9)
        for shopkeeper, count in fraud_ranking[:10]:  # Top 10
            pdf.cell(80, 8, shopkeeper[:35], 1, 0)
            pdf.cell(40, 8, str(count), 1, 1)
        pdf.ln(5)
    
    # Recent Fraud Logs
    fraud_logs = get_fraud_logs()
    if fraud_logs:
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, f"Recent Fraud Cases (Last 20)", 0, 1)
        pdf.set_font("Arial", "B", 9)
        pdf.cell(50, 8, "Customer", 1, 0)
        pdf.cell(40, 8, "Date", 1, 0)
        pdf.cell(60, 8, "Reason", 1, 0)
        pdf.cell(30, 8, "ML Score", 1, 1)
        
        pdf.set_font("Arial", size=8)
        for log in fraud_logs[:20]:
            pdf.cell(50, 8, log[1][:25], 1, 0)
            pdf.cell(40, 8, log[2][:10], 1, 0)
            pdf.cell(60, 8, log[3][:40], 1, 0)
            pdf.cell(30, 8, f"{log[4]:.2f}" if log[4] else "N/A", 1, 1)
    
    # Policy Fairness Analysis
    pdf.add_page()
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Policy Fairness Analysis", 0, 1)
    pdf.set_font("Arial", size=10)
    pdf.cell(0, 8, "This report analyzes subsidy distribution across income levels.", 0, 1)
    pdf.cell(0, 8, "Subsidy should primarily benefit Low and Middle income groups.", 0, 1)
    pdf.ln(5)
    
    # Save PDF
    report_dir = "pdf_reports"
    if not os.path.exists(report_dir):
        os.makedirs(report_dir)
    
    filename = f"government_analytics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    file_path = os.path.join(report_dir, filename)
    pdf.output(file_path)
    
    return file_path

