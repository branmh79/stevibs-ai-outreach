import requests
import json
import urllib.parse
import re
import asyncio
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from .base_tool import BaseTool


class MacaroniKIDEventsTool(BaseTool):
    name = "macaronikid_events"
    description = "Fetch family events from MacaroniKID using their API"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'cross-site'
        })
        
        # Location to MacaroniKID configuration mapping
        self.location_config = {
            "Covington, GA": {
                "url": "https://conyers.macaronikid.com/events/calendar",
                "townOwnerId": "58252a7a6f1aaf645c94f0da"
            },
            "Douglasville, GA": {
                "url": "N/A",
                "townOwnerId": None
            },
            "Duluth, GA": {
                "url": "https://duluth.macaronikid.com/events/calendar",
                "townOwnerId": "58252a7d6f1aaf645c94f28f"
            },
            "Gainesville, GA": {
                "url": "https://gainesvillega.macaronikid.com/events/calendar",
                "townOwnerId": "58252a7e6f1aaf645c94f2e1"
            },
            "Hiram, GA": {
                "url": "https://dallasga.macaronikid.com/events/calendar",
                "townOwnerId": "58252a7b6f1aaf645c94f137"
            },
            "Fayetteville, GA": {
                "url": "https://peachtreecity.macaronikid.com/events/calendar",
                "townOwnerId": "58252a7d6f1aaf645c94f26c"
            },
            "Snellville, GA": {
                "url": "https://snellville.macaronikid.com/events/calendar",
                "townOwnerId": "58252a7b6f1aaf645c94f16f"
            },
            "Stockbridge, GA": {
                "url": "https://mcdonough.macaronikid.com/events/calendar",
                "townOwnerId": "58252a7f6f1aaf645c94f3e1"
            },
            "Warner Robins, GA": {
                "url": "N/A",
                "townOwnerId": None
            },
            "Findlay, OH": {
                "url": "N/A",
                "townOwnerId": None
            },
        }
    
    async def _search_events(self, location: str) -> List[Dict[str, Any]]:
        """Search for MacaroniKID events using direct API calls"""
        try:
            location_info = self.location_config.get(location)
            
            if not location_info:
                print(f"[INFO] Location not configured: {location}")
                return self._get_mock_events(location)
            
            macaroni_url = location_info["url"]
            town_owner_id = location_info["townOwnerId"]
            
            if macaroni_url == "N/A" or not town_owner_id:
                print(f"[INFO] MacaroniKID not available for location: {location}")
                return []  # Return empty list instead of mock events
            
            # Set dynamic date range - today through next 2 weeks
            current_date = datetime.now(timezone.utc)
            two_weeks_from_now = current_date + timedelta(days=14)
            
            # Format dates for the API
            start_date = current_date.strftime('%Y-%m-%dT%H:%M:%S.000Z')
            end_date = two_weeks_from_now.strftime('%Y-%m-%dT%H:%M:%S.000Z')
            
            # Build the API query
            query = {
                "status": "active",
                "townOwner": town_owner_id,
                "startDate": start_date,
                "endDate": end_date
            }
            
            # Build the API URL
            query_param = urllib.parse.quote(json.dumps(query))
            api_url = f"https://api.macaronikid.com/api/v1/event/v2?query={query_param}&impression=true"
            
            # Make the API request
            headers = {
                'Accept': '*/*',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Referer': macaroni_url
            }
            
            response = requests.get(api_url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                try:
                    events_data = response.json()
                    print(f"[INFO] Retrieved {len(events_data)} events from MacaroniKID API")
                    
                    # Process the events
                    processed_events = []
                    for event in events_data:
                        processed_event = self._process_api_event(event)
                        if processed_event:
                            processed_events.append(processed_event)
                    
                    print(f"[INFO] Processed {len(processed_events)} events within 2-week window")
                    return processed_events
                    
                except json.JSONDecodeError as e:
                    print(f"[ERROR] Failed to parse API response: {e}")
                    return self._get_mock_events(location)
            else:
                print(f"[ERROR] API request failed with status {response.status_code}")
                return self._get_mock_events(location)
                
        except Exception as e:
            print(f"[ERROR] API call failed: {e}")
            return self._get_mock_events(location)
    
    def _process_api_event(self, event_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process a single event from the API response"""
        try:
            # Extract required fields
            event_id = event_data.get('_id', '')
            title = event_data.get('title', '')
            start_datetime = event_data.get('startDateTime', '')
            who = event_data.get('who', '')
            
            # Validate required fields
            if not event_id or not title or not start_datetime:
                return None
            
            # Filter events to next 2 weeks only
            try:
                start_date = datetime.fromisoformat(start_datetime.replace('Z', '+00:00'))
                current_date = datetime.now(timezone.utc)
                two_weeks_from_now = current_date + timedelta(days=14)
                
                # Skip events outside 2-week window
                if start_date < current_date or start_date > two_weeks_from_now:
                    return None
                    
            except ValueError:
                return None
            
            # Build event URL using the ID
            event_url = f"https://snellville.macaronikid.com/events/{event_id}"
            
            # Clean up the "who" field (remove HTML tags if present)
            who_cleaned = re.sub(r'<[^>]+>', '', who).strip() if who else ''
            
            return {
                'id': event_id,
                'title': title,
                'website': event_url,
                'startDateTime': start_datetime,
                'who': who_cleaned
            }
            
        except Exception:
            return None
    
    def _get_mock_events(self, location: str) -> List[Dict[str, Any]]:
        """Return mock events for testing when API is not available"""
        tomorrow = datetime.now() + timedelta(days=1)
        return [
            {
                'id': 'mock-123',
                'title': f'Mock MacaroniKID Event in {location}',
                'website': f'https://example.macaronikid.com/events/mock-123',
                'startDateTime': tomorrow.strftime('%Y-%m-%dT10:00:00.000Z'),
                'who': 'Everyone'
            }
        ]
    
    def execute(self, location: str) -> Dict[str, Any]:
        """Execute the MacaroniKID events search (synchronous)"""
        # Run the async version in a new event loop
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're already in an async context, use a thread pool
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self._search_events(location))
                    events = future.result()
            else:
                events = loop.run_until_complete(self._search_events(location))
        except RuntimeError:
            # No event loop, create a new one
            events = asyncio.run(self._search_events(location))
        
        return {
            'events': events,
            'location': location,
            'total_events': len(events),
            'source': 'MacaroniKID'
        }
    
    async def execute_async(self, location: str) -> Dict[str, Any]:
        """Execute the MacaroniKID events search (asynchronous)"""
        events = await self._search_events(location)
        
        return {
            'events': events,
            'location': location,
            'total_events': len(events),
            'source': 'MacaroniKID'
        }