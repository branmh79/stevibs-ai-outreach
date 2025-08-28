import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
from .base_tool import BaseTool
import re
import time
import json

class FacebookEventsTool(BaseTool):
    name = "facebook_events"
    description = "Fetch family events from Facebook using web scraping"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        })
    
    def _search_events(self, location: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search for Facebook events in a location using web scraping"""
        try:
            from urllib.parse import quote_plus

            # Exact filters blob supplied by user (covers this week, weekend, next week & next weekend)
            filters_blob = (
                "eyJmaWx0ZXJfZXZlbnRzX2RhdGVfcmFuZ2U6MCI6IntcIm5hbWVcIjpcImZpbHRlcl9ldmVudHNfZGF0ZVwiLFwiYXJnc1wiOlwiMjAyNS0wOC0yNX4yMDI1LTA4LTMxXCJ9IiwiZmlsdGVyX2V2ZW50c19kYXRlX3JhbmdlOjEiOiJ7XCJuYW1lXCI6XCJmaWx0ZXJfZXZlbnRzX2RhdGVcIixcImFyZ3NcIjpcIjIwMjUtMDgtMzB%2BMjAyNS0wOC0zMVwifSIsImZpbHRlcl9ldmVudHNfZGF0ZV9yYW5nZToyIjoie1wibmFtZVwiOlwiZmlsdGVyX2V2ZW50c19kYXRlXCIsXCJhcmdzXCI6XCIyMDI1LTA5LTAxfjIwMjUtMDktMDdcIn0iLCJmaWx0ZXJfZXZlbnRzX2RhdGVfcmFuZ2U6MyI6IntcIm5hbWVcIjpcImZpbHRlcl9ldmVudHNfZGF0ZVwiLFwiYXJnc1wiOlwiMjAyNS0wOS0wNn4yMDI1LTA5LTA3XCJ9In0%3D"
            )

            encoded_location = quote_plus(location)
            search_url_template = (
                f"https://www.facebook.com/events/search?q={{loc}}&filters={filters_blob}"
            )

            urls_to_try = [search_url_template.format(loc=encoded_location)]
            
            for search_url in urls_to_try:
                print(f"Trying URL: {search_url}")
                response = self.session.get(search_url, timeout=10)
                print(f"Response status: {response.status_code}")
                
                if response.status_code == 200:
                    print(f"Success with URL: {search_url}")
                    # Parse the HTML response
                    soup = BeautifulSoup(response.content, 'html.parser')
                    # HTML length can still be useful
                    print(f"HTML content length: {len(response.content)}")
                    
                    # Extract event information from the page
                    events = self._extract_events_from_page(soup, location)
                    print(f"Extracted {len(events)} events from HTML")

                    # Try to paginate using cursor to load more results (simulate scrolling)
                    all_events = events

                    # Extract initial GraphQL cursor from embedded JSON (end_cursor)
                    end_cursor_match = re.search(r'"end_cursor":"([^"]+)"', response.text)
                    if end_cursor_match:
                        next_cursor = end_cursor_match.group(1)
                        print(f"[DEBUG] Found initial end_cursor for GraphQL: {next_cursor[:20]}...")

                        # Extract tokens required for GraphQL POST
                        fb_dtsg_match = re.search(r'name="fb_dtsg" value="([^"]+)"', response.text)
                        lsd_match = re.search(r'name="lsd" value="([^"]+)"', response.text)
                        fb_dtsg = fb_dtsg_match.group(1) if fb_dtsg_match else None
                        lsd = lsd_match.group(1) if lsd_match else None

                        if fb_dtsg and lsd:
                            print("[DEBUG] Found fb_dtsg and lsd tokens; starting GraphQL pagination")
                            page_count = 0
                            max_pages = 5
                            while next_cursor and len(all_events) < 30 and page_count < max_pages:
                                variables = {
                                    "allow_streaming": False,
                                    "args": {
                                        "callsite": "comet:events_search",
                                        "config": {"exact_match": False},
                                        "context": {"bsid": ""},
                                        "experience": {"type": "EVENTS_DASHBOARD"},
                                        "filters": [
                                            {"name": "filter_events_date", "args": "2025-08-25~2025-09-07"}
                                        ],
                                        "text": location
                                    },
                                    "count": 7,
                                    "cursor": next_cursor,
                                    "feedLocation": "SEARCH",
                                    "fetch_filters": True
                                }

                                payload = {
                                    'doc_id': '32141493598774813',
                                    'variables': json.dumps(variables, separators=(',', ':')),
                                    'fb_dtsg': fb_dtsg,
                                    'lsd': lsd
                                }

                                print(f"[DEBUG] GraphQL page {page_count+1} cursor: {next_cursor[:15]}...")
                                gql_resp = self.session.post('https://www.facebook.com/api/graphql/', data=payload, timeout=10)
                                if gql_resp.status_code != 200:
                                    print(f"[DEBUG] GraphQL request failed: {gql_resp.status_code}")
                                    break
                                try:
                                    gql_json = gql_resp.json()
                                except Exception:
                                    break
                                edges = (gql_json.get('data', {})
                                         .get('serpResponse', {})
                                         .get('results', {})
                                         .get('edges', []))
                                new_events = []
                                for edge in edges:
                                    node_json = edge.get('node', {}).get('rendering_strategy', {})\
                                                .get('view_model', {}).get('profile', {})
                                    if node_json:
                                        # reuse extractor to convert
                                        ev = self._find_events_in_json(node_json)
                                        if ev:
                                            new_events.extend(ev)
                                print(f"[DEBUG] GraphQL extracted {len(new_events)} events")
                                all_events.extend(new_events)
                                # deduplicate
                                unique = {}
                                for ev in all_events:
                                    eid = ev.get('id') or ev.get('website')
                                    if eid and eid not in unique:
                                        unique[eid] = ev
                                all_events = list(unique.values())

                                page_info = gql_json.get('data', {})\
                                            .get('serpResponse', {})\
                                            .get('results', {})\
                                            .get('page_info', {})
                                next_cursor = page_info.get('end_cursor') if page_info else None
                                if not page_info.get('has_next_page'):
                                    next_cursor = None
                                page_count += 1
                        else:
                            print("[DEBUG] fb_dtsg or lsd token not found – cannot paginate via GraphQL")

                    return all_events[:30]
                else:
                    print(f"Failed with URL: {search_url}, status: {response.status_code}")
            
            print("All URLs failed, returning mock events for testing")
            # Return mock events so frontend can be tested
            return [
                {
                    "title": "Family Fun Day at Snellville Park",
                    "description": "Join us for a day of family activities, games, and entertainment at Snellville Park. Perfect for all ages!",
                    "date": "Next Saturday",
                    "address": "Snellville, GA",
                    "contact_email": "events@snellville.org",
                    "phone_number": "770-985-3500",
                    "website": "https://www.facebook.com/events/example1",
                    "source": "Facebook (Mock)",
                    "attending_count": 45,
                    "interested_count": 120
                },
                {
                    "title": "Community Family Festival",
                    "description": "Annual community celebration with food, music, and activities for the whole family. Free admission!",
                    "date": "This Sunday",
                    "address": "Snellville, GA",
                    "contact_email": "info@snellvillefestival.com",
                    "phone_number": "770-555-0123",
                    "website": "https://www.facebook.com/events/example2",
                    "source": "Facebook (Mock)",
                    "attending_count": 89,
                    "interested_count": 234
                }
            ]
            
        except Exception as e:
            print(f"Error searching Facebook events: {e}")
            return []
    
    def _extract_events_from_page(self, soup: BeautifulSoup, location: str) -> List[Dict[str, Any]]:
        """Extract event information from Facebook page HTML"""
        events = []
        
        try:
            # First, try to extract events from embedded JSON data (Facebook's preferred method)
            json_events = self._extract_events_from_json(soup)
            if json_events:
                print(f"Extracted {len(json_events)} events from JSON data")
                return json_events
            
            # Fallback to HTML parsing if JSON extraction fails
            print("JSON extraction failed, falling back to HTML parsing")
            
            # Look for event containers in the HTML
            event_selectors = [
                '[data-testid="event-card"]',
                '[data-testid="event-item"]',
                '.event-item',
                '.event-card',
                '[role="article"]',
                '[data-testid="event"]',
                '.event',
                '[data-testid="event-card-container"]',
                '.event-card-container'
            ]
            
            event_elements = []
            for selector in event_selectors:
                event_elements = soup.select(selector)
                print(f"Selector '{selector}' found {len(event_elements)} elements")
                if event_elements:
                    break
            
            if not event_elements:
                # Fallback: look for any divs that might contain event info
                event_elements = soup.find_all('div', class_=re.compile(r'event|Event'))
                print(f"Fallback regex found {len(event_elements)} elements")
            
            # Additional fallback: look for any elements containing "event" in text
            if not event_elements:
                event_elements = soup.find_all(text=re.compile(r'event', re.IGNORECASE))
                event_elements = [elem.parent for elem in event_elements if elem.parent]
                print(f"Text search found {len(event_elements)} elements")
            
            print(f"Total event elements found: {len(event_elements)}")
            
            for i, element in enumerate(event_elements[:10]):  # Limit to first 10 for debugging
                print(f"Processing element {i+1}: {str(element)[:200]}...")
                event_data = self._extract_single_event(element, location)
                if event_data:
                    events.append(event_data)
                    print(f"Successfully extracted event: {event_data['title']}")
                else:
                    print(f"Failed to extract event from element {i+1}")
            
        except Exception as e:
            print(f"Error extracting events: {e}")
        
        return events
    
    def _extract_events_from_json(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract events from embedded JSON data in Facebook pages"""
        events = []
        
        try:
            # Look for script tags containing JSON data
            script_tags = soup.find_all('script', type='application/json')
            
            for script in script_tags:
                try:
                    # Parse the JSON content
                    json_data = json.loads(script.string)
                    
                    # Navigate through the JSON structure to find events
                    events_found = self._find_events_in_json(json_data)
                    if events_found:
                        events.extend(events_found)
                        print(f"Found {len(events_found)} events in JSON script")
                        
                except json.JSONDecodeError:
                    continue
                except Exception as e:
                    print(f"Error parsing JSON script: {e}")
                    continue
            
            # Also look for script tags with data-sjs attribute (Facebook's format)
            sjs_scripts = soup.find_all('script', attrs={'data-sjs': True})
            
            for script in sjs_scripts:
                try:
                    # Parse the JSON content
                    json_data = json.loads(script.string)
                    
                    # Navigate through the JSON structure to find events
                    events_found = self._find_events_in_json(json_data)
                    if events_found:
                        events.extend(events_found)
                        print(f"Found {len(events_found)} events in SJS script")
                        
                except json.JSONDecodeError:
                    continue
                except Exception as e:
                    print(f"Error parsing SJS script: {e}")
                    continue
            
            # Deduplicate events by their unique Facebook id
            unique_events = {}
            for ev in events:
                ev_id = ev.get("id") or ev.get("url") or ev.get("website")
                if ev_id and ev_id not in unique_events:
                    unique_events[ev_id] = ev
            return list(unique_events.values())
            
        except Exception as e:
            print(f"Error extracting events from JSON: {e}")
            return []
    
    def _find_events_in_json(self, data: Any) -> List[Dict[str, Any]]:
        """Recursively search through JSON data to find event objects"""
        events = []
        
        if isinstance(data, dict):
            # Check if this is an event object
            if (data.get('__typename') == 'Event' and 
                data.get('name') and 
                data.get('id')):
                
                event = {
                    "title": data.get('name', 'Untitled Event'),
                    "description": data.get('description', 'No description available'),
                    "when": data.get('day_time_sentence', 'Date not specified'),
                    "address": data.get('event_place', {}).get('contextual_name', 'Location not specified'),
                    "contact_email": "",  # Facebook doesn't typically provide this
                    "phone_number": "",   # Facebook doesn't typically provide this
                    "website": data.get('url') or data.get('eventUrl', ''),
                    "source": "Facebook (JSON)",
                    "start_timestamp": data.get('start_timestamp'),
                    "attending_count": 0,
                    "interested_count": 0
                }
                
                # Extract social context if available
                social_context = data.get('social_context', {})
                if isinstance(social_context, dict) and social_context.get('text'):
                    # Parse text like "639 interested · 1 going"
                    text = social_context['text']
                    interested_match = re.search(r'(\d+)\s+interested', text)
                    if interested_match:
                        event['interested_count'] = int(interested_match.group(1))
                    
                    going_match = re.search(r'(\d+)\s+going', text)
                    if going_match:
                        event['attending_count'] = int(going_match.group(1))
                
                events.append(event)
                print(f"Found event: {event['title']}")
            
            # Recursively search through all values
            for value in data.values():
                events.extend(self._find_events_in_json(value))
                
        elif isinstance(data, list):
            # Recursively search through all items
            for item in data:
                events.extend(self._find_events_in_json(item))
        
        return events
    
    def _extract_single_event(self, element, location: str) -> Optional[Dict[str, Any]]:
        """Extract information from a single event element"""
        try:
            # Try to extract event title
            title = self._extract_text(element, [
                '[data-testid="event-title"]',
                '.event-title',
                'h1', 'h2', 'h3',
                '[role="heading"]'
            ])
            
            if not title or len(title) < 3:
                return None
            
            # Try to extract description
            description = self._extract_text(element, [
                '[data-testid="event-description"]',
                '.event-description',
                '.description',
                'p'
            ])
            
            # Try to extract date/time
            date_info = self._extract_text(element, [
                '[data-testid="event-time"]',
                '.event-time',
                '.time',
                'time'
            ])
            
            # Try to extract location
            event_location = self._extract_text(element, [
                '[data-testid="event-location"]',
                '.event-location',
                '.location'
            ])
            
            # Try to extract contact info
            contact_info = self._extract_text(element, [
                '.contact',
                '.contact-info',
                '.details'
            ])
            
            # Extract email and phone from contact info
            contact_email = ""
            phone_number = ""
            if contact_info:
                email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', contact_info)
                if email_match:
                    contact_email = email_match.group()
                
                phone_match = re.search(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', contact_info)
                if phone_match:
                    phone_number = phone_match.group()
            
            # Try to find event link
            event_link = self._extract_link(element)
            
            return {
                "title": title[:100] if title else "Untitled Event",
                "description": description[:300] + "..." if description and len(description) > 300 else (description or "No description available"),
                "date": date_info or "Date not specified",
                "address": event_location or location,
                "contact_email": contact_email,
                "phone_number": phone_number,
                "website": event_link or f"https://www.facebook.com/search/events/?q=family%20events%20{location.replace(' ', '%20')}",
                "source": "Facebook (Web)",
                "attending_count": 0,
                "interested_count": 0
            }
            
        except Exception as e:
            print(f"Error extracting single event: {e}")
            return None
    
    def _extract_text(self, element, selectors: List[str]) -> str:
        """Extract text content using multiple selectors"""
        for selector in selectors:
            try:
                found = element.select_one(selector)
                if found:
                    text = found.get_text(strip=True)
                    if text:
                        return text
            except:
                continue
        
        # Fallback: get all text from the element
        return element.get_text(strip=True)
    
    def _extract_link(self, element) -> str:
        """Extract link from an element"""
        try:
            link = element.find('a')
            if link and link.get('href'):
                href = link.get('href')
                if href.startswith('/'):
                    return f"https://www.facebook.com{href}"
                elif href.startswith('http'):
                    return href
        except:
            pass
        return ""
    
    def execute(self, location: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """Execute the Facebook events search using web scraping"""
        try:
            print(f"Searching Facebook events for location: {location}")
            events = self._search_events(location, start_date, end_date)
            # Filter events strictly by location keyword
            filtered_events = self._filter_events_by_location(events, location)
            print(f"Found {len(filtered_events)} Facebook events after location filtering")
            return filtered_events
        except Exception as e:
            print(f"Error fetching Facebook events: {e}")
            return []

    def _filter_events_by_location(self, events: List[Dict[str, Any]], location: str) -> List[Dict[str, Any]]:
        """Return only events whose address or title contains the location name (case-insensitive)."""
        location_lower = location.lower()
        result = []
        for ev in events:
            addr = (ev.get("address") or "").lower()
            title = (ev.get("title") or "").lower()
            if location_lower in addr or location_lower in title:
                result.append(ev)
        # If filtering removes everything, fall back to original list
        return result if result else events
