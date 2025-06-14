import os
from googleapiclient.discovery import build

def search_google_events(location: str, event_type: str):
    api_key = os.getenv("GOOGLE_CSE_API_KEY")
    cse_id = os.getenv("GOOGLE_CSE_ID")

    service = build("customsearch", "v1", developerKey=api_key)

    query = f"{event_type} events near {location}"
    results = service.cse().list(q=query, cx=cse_id, num=5).execute()

    events = []
    for item in results.get("items", []):
        events.append({
            "title": item.get("title"),
            "link": item.get("link"),
            "snippet": item.get("snippet")
        })

    return events
