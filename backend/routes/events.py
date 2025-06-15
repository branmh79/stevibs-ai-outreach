from fastapi import APIRouter, Query
from openai import OpenAI
from datetime import datetime
import os
import json
import re
from tools.google_search import search_google_events
from tools.ticketmaster import search_ticketmaster_events
from tools.openai_tool_schema import google_event_search_tool
from models.event import EnrichedEventList
from dateutil.parser import isoparse

router = APIRouter()

@router.get("/events")
async def get_events(
    location: str = Query(..., description="Location name (e.g. Snellville)"),
    event_type: str = Query("Summer Camp", description="Type of event to search for"),
    start_date: str = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(None, description="End date (YYYY-MM-DD)")
):
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    # Format ISO dates or fallback

    start = isoparse(start_date).isoformat() + "Z" if start_date else None
    end = isoparse(end_date).isoformat() + "Z" if end_date else None


    # First try Ticketmaster
    ticketmaster_results = search_ticketmaster_events(location, event_type, start, end)
    print("TICKETMASTER RESULTS:", ticketmaster_results)

    if ticketmaster_results:
        return ticketmaster_results  # ✅ Already structured, no GPT processing needed

    # Fallback to Google Search via GPT
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
            .replace("“", "\"")
            .replace("”", "\"")
            .replace("’", "'")
            .replace("‘", "'")
            .replace("None", "null")
        )
        structured_data = json.loads(cleaned_json)
        validated = EnrichedEventList.model_validate(structured_data)
        return [event.dict() for event in validated.events]

    except Exception as e:
        return {"error": f"Validation failed: {e}\nRaw content: {json_text}"}
