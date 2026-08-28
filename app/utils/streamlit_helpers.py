import streamlit as st


def safe_rerun():
    """Safely rerun the Streamlit app, handling different Streamlit versions"""
    if hasattr(st, 'rerun'):
        st.rerun()
    elif hasattr(st, 'experimental_rerun'):
        st.experimental_rerun()
    else:
        # Fallback: just raise an error with helpful message
        raise AttributeError(
            "Neither st.rerun() nor st.experimental_rerun() is available. "
            "Please update Streamlit to a newer version."
        )

