google_event_search_tool = {
    "type": "function",
    "function": {
        "name": "search_google_events",
        "description": "Searches Google for real-time upcoming events near a location and event category.",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "The city or area to search in (e.g., Snellville) If a city has GA, then it will be in Georgia."
                },
                "event_type": {
                    "type": "string",
                    "description": "The type of event to search for (e.g., summer camp, art show)"
                }
            },
            "required": ["location", "event_type"]
        }
    }
}

eventbrite_search_tool = {
    "type": "function",
    "function": {
        "name": "search_eventbrite_events",
        "description": "Searches Eventbrite for upcoming events near a location and category.",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City or region to search in"
                },
                "event_type": {
                    "type": "string",
                    "description": "Type of event (e.g., summer camp, comedy night)"
                }
            },
            "required": ["location", "event_type"]
        }
    }
}
