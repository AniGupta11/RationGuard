import streamlit as st
from datetime import datetime
from app.utils.db_ops import get_connection, update_notification_status


def display_notification_banner(user_id, role):
    month_year = datetime.now().strftime("%Y-%m")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, message, created_at
        FROM notifications
        WHERE user_id = ? AND (status = 'queued' OR status IS NULL)
        AND (month_year = ? OR month_year IS NULL)
        ORDER BY created_at DESC
        LIMIT 5
        """,
        (user_id, month_year),
    )
    rows = cur.fetchall()
    conn.close()

    if not rows:
        return

    title = f"Notifications for {role}"
    st.warning(title)
    for nid, msg, ts in rows:
        st.write(f"• {msg}")

    if st.button("Dismiss notifications"):
        for nid, _, _ in rows:
            try:
                update_notification_status(nid, "dismissed")
            except Exception:
                pass
        st.experimental_rerun()

