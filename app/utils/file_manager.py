# app/utils/file_manager.py

import os
from fpdf import FPDF
from datetime import datetime
from app.utils.pricing import COMMODITY_PRICES, COMMODITY_INFO

BILL_DIR = "pdf_bills"

def _sanitize_text(text):
    """Convert Unicode text to ASCII-safe string for FPDF latin1 encoding"""
    if not text:
        return ""
    # Replace common Unicode symbols with ASCII equivalents
    replacements = {
        '₹': 'Rs',
        '€': 'EUR',
        '£': 'GBP',
        '¥': 'JPY',
        '°': 'deg',
        '×': 'x',
        '÷': '/',
        '±': '+/-',
        'µ': 'u',
        '…': '...',
        '–': '-',
        '—': '-',
        '"': '"',
        '"': '"',
        ''': "'",
        ''': "'",
        '•': '*',
    }
    result = str(text)
    for unicode_char, ascii_char in replacements.items():
        result = result.replace(unicode_char, ascii_char)
    # Encode to ASCII, replacing any remaining non-ASCII with '?'
    try:
        return result.encode('ascii', 'replace').decode('ascii')
    except:
        # Fallback: remove all non-ASCII characters
        return ''.join(c if ord(c) < 128 else '?' for c in result)

def generate_bill_pdf(user_name, commodities_dict, total_amount):
    """Generate bill PDF for all 10 commodities"""
    # Create folder if it doesn't exist
    if not os.path.exists(BILL_DIR):
        os.makedirs(BILL_DIR)

    # Sanitize user_name for filename
    safe_name = _sanitize_text(user_name).replace(' ', '_').replace('?', '')
    bill_filename = f"bill_{safe_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    file_path = os.path.join(BILL_DIR, bill_filename)

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=10)
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)

    pdf.cell(200, 10, txt=_sanitize_text("RationGuard AI - Bill Receipt"), ln=True, align='C')

    pdf.set_font("Arial", size=12)
    pdf.ln(10)

    pdf.cell(200, 10, txt=_sanitize_text(f"Customer Name: {user_name}"), ln=True)
    pdf.ln(5)
    
    commodity_display = {
        key: COMMODITY_INFO[key] for key in COMMODITY_INFO
    }
    
    # Display all commodities with quantity > 0
    for commodity_key, (commodity_name, unit) in commodity_display.items():
        quantity = commodities_dict.get(commodity_key, 0)
        if quantity > 0:
            price = COMMODITY_PRICES.get(commodity_key, 0)
            line_text = f"{commodity_name}: {quantity} {unit} @ Rs{price}/{unit}"
            pdf.cell(200, 10, txt=_sanitize_text(line_text), ln=True)

    pdf.ln(5)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(200, 10, txt=_sanitize_text(f"Total Amount: Rs{total_amount:.2f}"), ln=True)

    pdf.output(file_path)

    return file_path
