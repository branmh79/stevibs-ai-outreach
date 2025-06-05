import streamlit as st
import requests

st.set_page_config(page_title="SteviB's AI Outreach", layout="centered")
st.title("SteviB's AI Outreach")

# Location options (from backend.data.locations)
LOCATION_OPTIONS = ["Snellville", "Loganville", "Grayson", "Lawrenceville"]

# Select location
location = st.selectbox("Choose a location to scout for events:", LOCATION_OPTIONS)

if st.button("Scrape Events"):
    with st.spinner("Scraping nearby events..."):
        try:
            res = requests.get("http://backend:8000/events", params={"location": location})
            data = res.json()

            if "error" in data:
                st.error(data["error"])
            elif isinstance(data, list) and data:
                st.success(f"Found {len(data)} events near {location}")
                for event in data:
                    st.subheader(event["event_name"])
                    st.markdown(f"**Description:** {event.get('description', 'N/A')}")
                    st.markdown(f"**Address:** {event['event_address']}")
                    if event.get("website"):
                        st.markdown(f"[Website]({event['website']})")
                    st.markdown(f"**Contact:** {event['contact_email']}")
                    st.markdown("---")
            else:
                st.warning("No events found.")

        except Exception as e:
            st.error(f"Failed to fetch events: {e}")
