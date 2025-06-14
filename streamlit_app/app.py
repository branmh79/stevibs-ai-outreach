import streamlit as st
import requests
import sys
import os

st.set_page_config(page_title="SteviB's AI Outreach", layout="centered")
st.title("SteviB's AI Outreach")

# Add backend to path
sys.path.append("/backend")
from data.locations import LOCATION_ADDRESSES
LOCATION_OPTIONS = list(LOCATION_ADDRESSES.keys())

# Select location and event type
location = st.selectbox("Choose a location to scout for events:", LOCATION_OPTIONS)
COMMON_EVENT_TYPES = ["Karaoke", "Food Festivals", "Craft Fairs", "Live Music Events", "Cultural Festivals", "Summer Camp", "Water Park", "Recreation Center", "Art Class", "Sports Meetup"]
event_type = st.selectbox("Filter by event type:", COMMON_EVENT_TYPES)

if st.button("Scrape Events"):
    with st.spinner("Searching for real events..."):
        try:
            res = requests.get("http://backend:8000/events", params={"location": location, "event_type": event_type})
            data = res.json()

            if "error" in data:
                st.error(data["error"])
            elif isinstance(data, list) and data:
                st.success(f"Found {len(data)} events near {location}")
                for event in data:
                    st.subheader(event.get("title", "Untitled Event"))

                    if event.get("date"):
                        st.markdown(f"**Date:** {event['date']}")

                    if event.get("description"):
                        st.markdown(f"**Description:** {event['description']}")

                    if event.get("website"):
                        st.markdown(f"[Website]({event['website']})")

                    if event.get("contact_email"):
                        st.markdown(f"**Email:** {event['contact_email']}")

                    if event.get("phone"):
                        st.markdown(f"**Phone:** {event['phone']}")

                    st.markdown("---")
            else:
                st.warning("No events found.")

        except Exception as e:
            st.error(f"Failed to fetch events: {e}")
