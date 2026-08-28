import pywhatkit as kit
from datetime import datetime
import streamlit as st

# Government WhatsApp number (STATIC)
GOVT_PHONE = "+919672765791"


def send_whatsapp_alert(customer_phone: str, message: str):
    """Send WhatsApp alert to customer from government number"""

    if not customer_phone.startswith("+91") or len(customer_phone) != 13:
        st.warning("Invalid customer phone for WhatsApp alert.")
        return False

    try:
        now = datetime.now()
        send_hour = now.hour
        send_minute = now.minute + 1  # Must be scheduled at least 1 min ahead

        kit.sendwhatmsg(
            customer_phone,
            message,
            send_hour,
            send_minute,
            wait_time=10,     # Wait before sending
            tab_close=True    # Auto-close tab after sending
        )

        st.success("WhatsApp alert scheduled successfully to customer!")
        return True

    except Exception as e:
        st.error(f"WhatsApp alert failed: {e}")
        return False