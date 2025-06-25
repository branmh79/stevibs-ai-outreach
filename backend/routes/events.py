from fastapi import APIRouter, Query
from openai import OpenAI
from datetime import datetime
import os
import json
import re
from typing import List, Dict, Any
from tools.google_search import GoogleSearchTool
from tools.ticketmaster import TicketmasterTool
from tools.eventbrite import EventbriteTool
from tools.contact_scraper import ContactScraperTool
from tools.openai_tool_schema import google_event_search_tool
from models.event import EnrichedEventList
from dateutil.parser import isoparse
from tools.unified_event_search import UnifiedEventSearchTool
from tools.family_event_search import FamilyEventSearchTool

router = APIRouter()

@router.get("/events")
async def get_events(
    location: str = Query(..., description="Location name (e.g. Snellville)"),
    event_type: str = Query("Summer Camp", description="Type of event to search for"),
    start_date: str = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(None, description="End date (YYYY-MM-DD)"),
    use_mock: bool = Query(False, description="Use mock data for testing")
):
    """
    Search for events using multiple sources with standardized tool interface.
    Returns events from Ticketmaster, Eventbrite, Google Search, and contact scraping.
    """
    
    # Initialize tools
    ticketmaster_tool = TicketmasterTool()
    eventbrite_tool = EventbriteTool()
    google_tool = GoogleSearchTool()
    scraper_tool = ContactScraperTool()
    
    all_events = []
    
    # Prepare input data for tools
    base_input = {
        "location": location,
        "event_type": event_type
    }
    
    # Add date parameters if provided
    if start_date:
        base_input["start_date"] = start_date
    if end_date:
        base_input["end_date"] = end_date
    
    # Search Ticketmaster
    print("🔍 Searching Ticketmaster...")
    ticketmaster_result = ticketmaster_tool(base_input)
    if ticketmaster_result["success"]:
        all_events.extend(ticketmaster_result["events"])
        print(f"✅ Found {ticketmaster_result['count']} Ticketmaster events")
    else:
        print(f"❌ Ticketmaster error: {ticketmaster_result['error']}")
    
    # Search Eventbrite
    print("🔍 Searching Eventbrite...")
    eventbrite_result = eventbrite_tool(base_input)
    if eventbrite_result["success"]:
        all_events.extend(eventbrite_result["events"])
        print(f"✅ Found {eventbrite_result['count']} Eventbrite events")
    else:
        print(f"❌ Eventbrite error: {eventbrite_result['error']}")
    
    # Search Google (if no events found from other sources)
    if not all_events:
        print("🔍 Searching Google...")
        google_result = google_tool(base_input)
        if google_result["success"]:
            all_events.extend(google_result["events"])
            print(f"✅ Found {google_result['count']} Google events")
        else:
            print(f"❌ Google error: {google_result['error']}")
    
    # Scrape contact information for additional events
    print("🔍 Scraping contact information...")
    scraper_input = {
        "location": location,
        "query": event_type,
        "use_mock": use_mock
    }
    scraper_result = scraper_tool(scraper_input)
    if scraper_result["success"]:
        # Convert Place objects to event format
        scraped_events = []
        for place in scraper_result["places"]:
            scraped_events.append({
                "title": place.get("name"),
                "description": place.get("description"),
                "date": None,  # Scraped events don't have dates
                "website": place.get("website"),
                "contact_email": place.get("contact_email"),
                "phone": place.get("phone_number")
            })
        all_events.extend(scraped_events)
        print(f"✅ Found {scraper_result['count']} scraped events")
    else:
        print(f"❌ Scraper error: {scraper_result['error']}")
    
    # Remove duplicates based on title and website
    unique_events = _deduplicate_events(all_events)
    
    return {
        "success": True,
        "events": unique_events,
        "total_count": len(unique_events),
        "sources": {
            "ticketmaster": ticketmaster_result.get("count", 0) if ticketmaster_result["success"] else 0,
            "eventbrite": eventbrite_result.get("count", 0) if eventbrite_result["success"] else 0,
            "google": google_result.get("count", 0) if "google_result" in locals() and google_result["success"] else 0,
            "scraped": scraper_result.get("count", 0) if scraper_result["success"] else 0
        }
    }

def _deduplicate_events(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove duplicate events based on title and website."""
    seen = set()
    unique_events = []
    
    for event in events:
        title = event.get("title", "").lower().strip()
        website = event.get("website", "")
        # Convert HttpUrl to string before calling lower()
        website_str = str(website).lower().strip() if website else ""
        
        # Create a unique key
        key = f"{title}|{website_str}"
        
        if key not in seen:
            seen.add(key)
            unique_events.append(event)
    
    return unique_events

@router.get("/events/legacy")
async def get_events_legacy(
    location: str = Query(..., description="Location name (e.g. Snellville)"),
    event_type: str = Query("Summer Camp", description="Type of event to search for"),
    start_date: str = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(None, description="End date (YYYY-MM-DD)")
):
    """
    Legacy endpoint that maintains the old behavior for backward compatibility.
    """
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    # Format ISO dates or fallback
    start = isoparse(start_date).isoformat() + "Z" if start_date else None
    end = isoparse(end_date).isoformat() + "Z" if end_date else None

    # First try Ticketmaster
    from tools.ticketmaster import search_ticketmaster_events
    ticketmaster_results = search_ticketmaster_events(location, event_type, start, end)
    print("TICKETMASTER RESULTS:", ticketmaster_results)

    if ticketmaster_results:
        return ticketmaster_results  # ✅ Already structured, no GPT processing needed

    # Fallback to Google Search via GPT
    from tools.google_search import search_google_events
    
    search_messages = [{
        "role": "user",
        "content": (
            f"Find as many real, local {event_type} events happening near {location} as possible. "
            "Focus on results that look like actual events, not general programs or businesses. "
            "Include the event name, a short description, and contact info if available. "
            "If a city has GA, then it will be in Georgia. Try to keep events within about a month from now."
        )
    }]
    tools = [google_event_search_tool]
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=search_messages,
        tools=tools,
        tool_choice="auto"
    )
    tool_call = response.choices[0].message.tool_calls[0]
    args = json.loads(tool_call.function.arguments)
    print("TOOL SELECTED:", tool_call.function.name)
    print("TOOL ARGS:", args)

    search_results = search_google_events(args["location"], args["event_type"])
    print("GOOGLE SEARCH RESULTS:", search_results)
    raw_results = json.dumps(search_results, indent=2)

    # Post-process using GPT
    post_prompt = [
        {"role": "system", "content": (
            "You are an assistant that extracts structured event data from search results. "
            "Return anything that resembles a real event, even if some details are missing. "
            "Each item should include:\n- title\n- short description\n- website (if available)\n"
            "- contact_email (if available)\n- phone (if available). "
            "Respond ONLY with JSON in this format:\n\n"
            "{'events': [{'title': ..., 'description': ..., 'contact_email': ..., 'phone': ..., 'website': ...}, ...]}"
        )},
        {"role": "user", "content": raw_results}
    ]

    post_response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=post_prompt
    )

    json_text = post_response.choices[0].message.content.strip()
    print("GPT JSON RAW RESPONSE:", json_text)

    match = re.search(r"\{.*\}", json_text, re.DOTALL)
    if not match:
        return {"error": "Could not parse GPT output"}

    try:
        json_block = match.group(0)
        cleaned_json = (
            json_block
            .replace(""", "\"")
            .replace(""", "\"")
            .replace("'", "'")
            .replace("'", "'")
            .replace("None", "null")
        )
        structured_data = json.loads(cleaned_json)
        validated = EnrichedEventList.model_validate(structured_data)
        return [event.dict() for event in validated.events]

    except Exception as e:
        return {"error": f"Validation failed: {e}\nRaw content: {json_text}"}

@router.get("/events/unified")
async def get_events_unified(
    location: str = Query(..., description="Location name (e.g. Snellville)"),
    event_type: str = Query("Summer Camp", description="Type of event to search for"),
    use_mock: bool = Query(False, description="Use mock data for testing"),
    search_radius: int = Query(5000, description="Search radius in meters")
):
    """
    Web scraping focused endpoint for finding local events.
    """
    input_data = {
        "location": location,
        "event_type": event_type,
        "use_mock": use_mock,
        "search_radius": search_radius
    }
    
    tool = UnifiedEventSearchTool()
    result = tool(input_data)
    
    return result

@router.get("/events/family")
async def get_family_events(
    location: str = Query(..., description="Location name (e.g. Snellville)"),
    use_mock: bool = Query(False, description="Use mock data for testing"),
    search_radius: int = Query(5000, description="Search radius in meters")
):
    """
    Family-focused endpoint for finding events relevant to families with kids 7-18.
    Automatically searches for summer camps, after-school programs, youth sports, etc.
    """
    input_data = {
        "location": location,
        "use_mock": use_mock,
        "search_radius": search_radius
    }
    
    tool = FamilyEventSearchTool()
    result = tool(input_data)
    
    return result
