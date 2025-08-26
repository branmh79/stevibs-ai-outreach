import streamlit as st
import requests
import sys
import os
from datetime import date

st.set_page_config(page_title="SteviB's AI Outreach", layout="centered")
st.title("SteviB's AI Outreach")

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))
from data.locations import LOCATION_ADDRESSES
LOCATION_OPTIONS = list(LOCATION_ADDRESSES.keys())

# Select location only
location = st.selectbox("Choose a location to scout for family events:", LOCATION_OPTIONS)

# Select date range
col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("Start date (optional)", value=None)
with col2:
    end_date = st.date_input("End date (optional)", value=None)

# Convert dates to strings if selected
start_str = start_date.isoformat() if start_date else None
end_str = end_date.isoformat() if end_date else None

if st.button("Find Family Events"):
    with st.spinner("Searching for family-focused events..."):
        try:
            params = {
                "location": location
            }
            if start_str:
                params["start_date"] = start_str
            if end_str:
                params["end_date"] = end_str

            # Use the unified endpoint
            res = requests.get("http://backend:8000/events/family", params=params)
            data = res.json()

            if "error" in data:
                st.error(data["error"])
            elif data.get("success") and data.get("events"):
                events = data["events"]
                st.success(f"Found {len(events)} family events near {location}")
                
                # Source breakdown no longer displayed
                
                for event in events:
                    st.subheader(event.get("title", "Untitled Event"))

                    if event.get("date"):
                        st.markdown(f"**Date:** {event['date']}")

                    if event.get("description"):
                        st.markdown(f"**Description:** {event['description']}")

                    if event.get("website"):
                        st.markdown(f"[Website]({event['website']})")

                    # Always show Email and Phone fields, display 'N/A' if missing
                    st.markdown(f"**Email:** {event.get('contact_email') if event.get('contact_email') else 'N/A'}")
                    st.markdown(f"**Phone:** {event.get('phone_number') if event.get('phone_number') else 'N/A'}")

                    if event.get("address"):
                        st.markdown(f"**Address:** {event['address']}")

                    st.markdown("---")
            else:
                st.warning("No family events found.")

        except Exception as e:
            st.error(f"Failed to fetch events: {e}")
