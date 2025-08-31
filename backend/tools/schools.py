import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
from .base_tool import BaseTool
import re
import time
from datetime import datetime, timedelta, date
import logging
import pytz

class SchoolsTool(BaseTool):
    name = "schools"
    description = "Fetch school events from school website calendars using web scraping"
    
    # Date filtering configuration - easily customizable
    DEFAULT_DAYS_AHEAD = 14  # Default: next 2 weeks
    INCLUDE_TODAY = True     # Include events happening today
    
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
            'Cache-Control': 'max-age=0'
        })
        
        # Location to school URLs mapping - easily expandable
        self.location_config = {
            "Snellville, GA": {
                "elementary": [
                    "https://brookwoodes.gcpsk12.org/calendar",
                    "https://shilohes.gcpsk12.org/calendar-c3"
                ],
                "middle": [
                    "https://snellvillems.gcpsk12.org/calendar",
                    "https://shilohms.gcpsk12.org/calendar"
                ],
                "high": [
                    "https://southgwinnetths.gcpsk12.org/calendar",
                    "https://shilohhs.gcpsk12.org/calendar"
                ]
            }
            # TODO: Add other locations as needed
            # "Other City, GA": {
            #     "elementary": [...],
            #     "middle": [...],
            #     "high": [...]
            # }
        }
    
    def execute(self, location: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, Any]:
        """Execute the school events search using web scraping"""
        try:
            print(f"[INFO] Starting school events search for location: {location}")
            
            # Get school URLs for the location
            school_config = self.location_config.get(location, {})
            if not school_config:
                print(f"[INFO] No school configuration found for location: {location}")
                return {
                    'success': True,
                    'events': [],
                    'message': f"No school URLs configured for {location}"
                }
            
            all_events = []
            total_urls = 0
            
            # Process each school type (elementary, middle, high)
            for school_type, urls in school_config.items():
                if not urls:
                    print(f"[INFO] No {school_type} school URLs configured for {location}")
                    continue
                
                print(f"[INFO] Processing {len(urls)} {school_type} school(s) for {location}")
                total_urls += len(urls)
                
                for i, url in enumerate(urls):
                    try:
                        print(f"[INFO] Scraping {school_type} school {i+1}/{len(urls)}: {url}")
                        events = self._scrape_school_calendar(url, school_type, location)
                        all_events.extend(events)
                        print(f"[INFO] Found {len(events)} events from {url}")
                        
                        # Be respectful with rate limiting
                        if i < len(urls) - 1:  # Don't sleep after last URL
                            time.sleep(1)  # 1 second delay between requests
                            
                    except Exception as e:
                        print(f"[ERROR] Error scraping {url}: {str(e)}")
                        continue
            
            # Deduplicate events by title and date
            unique_events = self._deduplicate_events(all_events)
            
            # Filter events by date range (today + next 2 weeks by default)
            date_filtered_events = self._filter_events_by_date_range(unique_events)
            
            print(f"[INFO] Total: Found {len(unique_events)} unique school events from {total_urls} URLs")
            print(f"[INFO] After date filtering: {len(date_filtered_events)} events in the next {self.DEFAULT_DAYS_AHEAD} days")
            
            # Consolidate recurring events (same title, different dates)
            consolidated_events = self._consolidate_recurring_events(date_filtered_events)
            print(f"[INFO] After consolidating recurring events: {len(consolidated_events)} events")
            
            return {
                'success': True,
                'events': consolidated_events,
                'message': f"Found {len(consolidated_events)} school events from {total_urls} sources (next {self.DEFAULT_DAYS_AHEAD} days)"
            }
            
        except Exception as e:
            print(f"[ERROR] Error in school events search: {str(e)}")
            return {
                'success': False,
                'events': [],
                'error': str(e)
            }
    
    def _scrape_school_calendar(self, url: str, school_type: str, location: str) -> List[Dict[str, Any]]:
        """Scrape events from a single school calendar URL"""
        events = []
        
        try:
            print(f"[DEBUG] Fetching calendar from: {url}")
            response = self.session.get(url, timeout=10)
            
            if response.status_code != 200:
                print(f"[WARNING] HTTP {response.status_code} for {url}")
                return events
            
            # Parse HTML content
            soup = BeautifulSoup(response.content, 'html.parser')
            print(f"[DEBUG] HTML content length: {len(response.content)} bytes")
            
            # Extract school name from URL or page title
            school_name = self._extract_school_name(soup, url)
            
            # Debug: Show what calendar structure we're dealing with
            # self._debug_calendar_structure(soup, school_name, url)  # Disabled - working!
            
            # Try multiple calendar extraction strategies
            events = self._extract_calendar_events(soup, school_name, school_type, location, url)
            
            print(f"[DEBUG] Extracted {len(events)} events from {school_name}")
            return events
            
        except Exception as e:
            print(f"[ERROR] Error scraping {url}: {str(e)}")
            return []
    
    def _extract_school_name(self, soup: BeautifulSoup, url: str) -> str:
        """Extract school name from page title or URL"""
        try:
            # Try to get from page title
            title_tag = soup.find('title')
            if title_tag:
                title = title_tag.get_text().strip()
                print(f"[DEBUG] Raw page title: '{title}'")
                
                # Clean up common title patterns
                title = re.sub(r' - Calendar.*$', '', title)
                title = re.sub(r' Calendar.*$', '', title)
                title = re.sub(r' \| .*$', '', title)
                title = re.sub(r'^Calendar - ', '', title)  # Remove "Calendar - " prefix
                title = re.sub(r'^Calendar$', '', title)    # Remove standalone "Calendar"
                
                print(f"[DEBUG] Cleaned page title: '{title}'")
                if title and len(title) > 5:
                    return title
            
            # Enhanced URL-based school name mapping for Gwinnett County schools
            from urllib.parse import urlparse
            domain = urlparse(url).netloc.lower()
            
            # Known school mappings
            school_mappings = {
                'brookwoodes.gcpsk12.org': 'Brookwood Elementary School',
                'shilohes.gcpsk12.org': 'Shiloh Elementary School',
                'snellvillems.gcpsk12.org': 'Snellville Middle School', 
                'shilohms.gcpsk12.org': 'Shiloh Middle School',
                'southgwinnetths.gcpsk12.org': 'South Gwinnett High School',
                'shilohhs.gcpsk12.org': 'Shiloh High School'
            }
            
            if domain in school_mappings:
                return school_mappings[domain]
            
            # Fallback to URL parsing for unknown schools
            school_name = domain.replace('www.', '').replace('.com', '').replace('.org', '').replace('.edu', '')
            return school_name.title()
            
        except Exception:
            return "Unknown School"
    
    def _extract_calendar_events(self, soup: BeautifulSoup, school_name: str, school_type: str, location: str, url: str) -> List[Dict[str, Any]]:
        """Extract events from school calendar HTML using multiple strategies"""
        events = []
        
        # Strategy 1: Look for common calendar event selectors
        calendar_selectors = [
            # FinalSite calendar system (used by Gwinnett County schools)
            # Try multiple FinalSite selectors to catch different event types
            '.fsCalendarDayBox .fsCalendarInfo',  # Daily events in day view
            '.fsCalendarEventGrid .fsCalendarDayBox',  # Day boxes with events
            '.fsCalendarDayBox',  # All day boxes
            '.fsCalendarEvent',  # Individual events
            '.fsCalendarLongEvent',  # Long/multi-day events  
            '.fsCalendarDayViewEvent',  # Day view events
            '[class*="fsCalendar"][class*="Event"]',  # Any FinalSite event class
            
            # Standard calendar selectors
            '.calendar-event',
            '.event',
            '.fc-event',  # FullCalendar
            '.tribe-events-list-event',  # The Events Calendar plugin
            '.event-item',
            '.calendar-item',
            '[class*="event"]',
            '[class*="calendar"]',
            '.vevent',  # Microformat
        ]
        
        for selector in calendar_selectors:
            try:
                event_elements = soup.select(selector)
                if event_elements:
                    print(f"[DEBUG] Found {len(event_elements)} events using selector: {selector}")
                    for i, element in enumerate(event_elements):
                        event = self._parse_event_element(element, school_name, school_type, location, url)
                        if event:
                            events.append(event)
                            print(f"[DEBUG] ✓ Parsed: {event['title']} | Date: {event['when']}")
                        # Removed verbose debug output
                    
                    # Continue trying other selectors to get all events
            except Exception as e:
                print(f"[DEBUG] Error with selector {selector}: {e}")
                continue
        
        # Remove duplicate events based on title and date
        unique_events = []
        seen_events = set()
        for event in events:
            event_key = f"{event['title']}_{event['when']}"
            if event_key not in seen_events:
                unique_events.append(event)
                seen_events.add(event_key)
        events = unique_events
        
        # Strategy 2: Handle Google Calendar iframes
        if not events:
            events.extend(self._extract_google_calendar_events(soup, school_name, school_type, location, url))

        # Strategy 3: Look for structured data (JSON-LD, microdata)
        if not events:
            events.extend(self._extract_structured_data_events(soup, school_name, school_type, location, url))
        
        # Strategy 4: Text-based pattern matching for calendar content
        if not events:
            events.extend(self._extract_text_pattern_events(soup, school_name, school_type, location, url))
        
        return events
    
    def _extract_google_calendar_events(self, soup: BeautifulSoup, school_name: str, school_type: str, location: str, url: str) -> List[Dict[str, Any]]:
        """Extract events from Google Calendar iframes"""
        events = []
        
        try:
            # Look for Google Calendar iframes
            google_iframes = soup.find_all('iframe', src=lambda x: x and 'calendar.google.com' in str(x))
            
            if not google_iframes:
                print(f"[DEBUG] No Google Calendar iframes found")
                return events
            
            print(f"[DEBUG] Found {len(google_iframes)} Google Calendar iframe(s)")
            
            for i, iframe in enumerate(google_iframes):
                iframe_src = iframe.get('src', '')
                print(f"[DEBUG] Processing Google Calendar iframe {i+1}: {iframe_src[:100]}...")
                
                # Extract calendar ID from the iframe src
                calendar_id = self._extract_calendar_id_from_iframe(iframe_src)
                if not calendar_id:
                    print(f"[DEBUG] Could not extract calendar ID from iframe")
                    continue
                
                print(f"[DEBUG] Extracted calendar ID: {calendar_id}")
                
                # Try to fetch events using Google Calendar's public API
                calendar_events = self._fetch_google_calendar_events(calendar_id, school_name, school_type, location, url)
                events.extend(calendar_events)
                
                print(f"[DEBUG] Extracted {len(calendar_events)} events from Google Calendar iframe")
        
        except Exception as e:
            print(f"[DEBUG] Error extracting Google Calendar events: {e}")
        
        return events
    
    def _extract_calendar_id_from_iframe(self, iframe_src: str) -> Optional[str]:
        """Extract Google Calendar ID from iframe src URL"""
        try:
            import re
            from urllib.parse import unquote
            
            # Decode URL encoding
            decoded_src = unquote(iframe_src)
            
            # Look for calendar ID patterns in Google Calendar embed URLs
            patterns = [
                r'src=([^&\s]+)(?:&|$)',  # src parameter
                r'calendars/([^/\s&]+)',   # in calendars path
                r'cid=([^&\s]+)',          # cid parameter
                r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',  # email format
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, decoded_src)
                for match in matches:
                    # Clean up the match
                    calendar_id = match.strip()
                    if '@' in calendar_id or calendar_id.endswith('.calendar.google.com'):
                        # This looks like a valid calendar ID
                        return calendar_id
            
            # If no specific pattern found, try to extract any email-like string
            email_pattern = r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
            email_matches = re.findall(email_pattern, decoded_src)
            if email_matches:
                return email_matches[0]
            
            print(f"[DEBUG] No calendar ID patterns found in: {decoded_src[:200]}...")
            return None
            
        except Exception as e:
            print(f"[DEBUG] Error extracting calendar ID: {e}")
            return None
    
    def _fetch_google_calendar_events(self, calendar_id: str, school_name: str, school_type: str, location: str, url: str) -> List[Dict[str, Any]]:
        """Fetch events from Google Calendar using public calendar access"""
        events = []
        
        try:
            # For embedded public calendars, we can try to access the public feed
            # Google Calendar public feeds are available in different formats
            
            # Try the public XML feed first
            public_feed_urls = [
                f"https://calendar.google.com/calendar/feeds/{calendar_id}/public/full",
                f"https://calendar.google.com/calendar/ical/{calendar_id}/public/basic.ics",
                f"https://www.google.com/calendar/feeds/{calendar_id}/public/full?alt=json",
            ]
            
            for feed_url in public_feed_urls:
                try:
                    print(f"[DEBUG] Trying Google Calendar feed: {feed_url[:80]}...")
                    response = self.session.get(feed_url, timeout=10)
                    
                    if response.status_code == 200:
                        print(f"[DEBUG] Successfully fetched Google Calendar feed")
                        
                        # Try to parse based on content type
                        content_type = response.headers.get('content-type', '').lower()
                        
                        if 'json' in content_type:
                            events.extend(self._parse_google_calendar_json(response.text, school_name, school_type, location, url))
                        elif 'xml' in content_type or 'atom' in content_type:
                            events.extend(self._parse_google_calendar_xml(response.text, school_name, school_type, location, url))
                        elif 'calendar' in content_type or response.text.startswith('BEGIN:VCALENDAR'):
                            events.extend(self._parse_google_calendar_ics(response.text, school_name, school_type, location, url))
                        
                        if events:
                            print(f"[DEBUG] Successfully parsed {len(events)} events from Google Calendar feed")
                            break
                    else:
                        print(f"[DEBUG] Google Calendar feed returned {response.status_code}")
                        
                except Exception as e:
                    print(f"[DEBUG] Error with feed {feed_url[:50]}...: {e}")
                    continue
            
            # Fallback: Try to scrape the calendar's public HTML view
            if not events:
                events.extend(self._scrape_google_calendar_html(calendar_id, school_name, school_type, location, url))
        
        except Exception as e:
            print(f"[DEBUG] Error fetching Google Calendar events: {e}")
        
        return events
    
    def _parse_google_calendar_json(self, json_content: str, school_name: str, school_type: str, location: str, url: str) -> List[Dict[str, Any]]:
        """Parse Google Calendar JSON feed"""
        events = []
        try:
            import json
            data = json.loads(json_content)
            
            # Parse Google Calendar JSON format
            feed_entries = data.get('feed', {}).get('entry', [])
            
            for entry in feed_entries:
                title = entry.get('title', {}).get('$t', '')
                
                # Extract date/time
                when_list = entry.get('gd$when', [])
                event_date = "Date not specified"
                if when_list:
                    start_time = when_list[0].get('startTime', '')
                    if start_time:
                        event_date = self._format_date(start_time)
                
                if title and len(title) > 3:
                    events.append({
                        'title': title,
                        'date': event_date,
                        'when': event_date,
                        'location': location,
                        'address': school_name,  # Show just the school name
                        'description': f"Google Calendar event from {school_name}",
                        'website': url,  # School's calendar page
                        'url': url,
                        'source': f"Schools ({school_type.title()})",
                        'school_name': school_name,
                        'school_type': school_type,
                        'contact_email': None,
                        'phone_number': None,
                        'interested_count': 0,
                        'attending_count': 0
                    })
        
        except Exception as e:
            print(f"[DEBUG] Error parsing Google Calendar JSON: {e}")
        
        return events
    
    def _parse_google_calendar_xml(self, xml_content: str, school_name: str, school_type: str, location: str, url: str) -> List[Dict[str, Any]]:
        """Parse Google Calendar XML/Atom feed"""
        events = []
        try:
            from xml.etree import ElementTree as ET
            
            root = ET.fromstring(xml_content)
            
            # Handle different XML namespaces
            namespaces = {
                'atom': 'http://www.w3.org/2005/Atom',
                'gd': 'http://schemas.google.com/g/2005'
            }
            
            # Find entry elements
            entries = root.findall('.//atom:entry', namespaces) or root.findall('.//entry')
            
            for entry in entries:
                # Extract title
                title_elem = entry.find('.//atom:title', namespaces) or entry.find('.//title')
                title = title_elem.text if title_elem is not None else ''
                
                # Extract date/time
                when_elem = entry.find('.//gd:when', namespaces)
                event_date = "Date not specified"
                if when_elem is not None:
                    start_time = when_elem.get('startTime', '')
                    if start_time:
                        event_date = self._format_date(start_time)
                
                if title and len(title) > 3:
                    events.append({
                        'title': title,
                        'date': event_date,
                        'when': event_date,
                        'location': location,
                        'address': school_name,  # Show just the school name
                        'description': f"Google Calendar event from {school_name}",
                        'website': url,  # School's calendar page
                        'url': url,
                        'source': f"Schools ({school_type.title()})",
                        'school_name': school_name,
                        'school_type': school_type,
                        'contact_email': None,
                        'phone_number': None,
                        'interested_count': 0,
                        'attending_count': 0
                    })
        
        except Exception as e:
            print(f"[DEBUG] Error parsing Google Calendar XML: {e}")
        
        return events
    
    def _parse_google_calendar_ics(self, ics_content: str, school_name: str, school_type: str, location: str, url: str) -> List[Dict[str, Any]]:
        """Parse Google Calendar ICS (iCal) format"""
        events = []
        try:
            # Simple ICS parsing without external dependencies
            lines = ics_content.split('\n')
            current_event = {}
            in_event = False
            
            for line in lines:
                line = line.strip()
                
                if line == 'BEGIN:VEVENT':
                    in_event = True
                    current_event = {}
                elif line == 'END:VEVENT' and in_event:
                    in_event = False
                    
                    # Process the completed event
                    title = current_event.get('SUMMARY', '')
                    start_time = current_event.get('DTSTART', '')
                    
                    event_date = "Date not specified"
                    if start_time:
                        event_date = self._format_date(start_time)
                    
                    if title and len(title) > 3:
                        events.append({
                            'title': title,
                            'date': event_date,
                            'when': event_date,
                            'location': location,
                            'address': school_name,  # Show just the school name
                            'description': f"Google Calendar event from {school_name}",
                            'website': url,  # School's calendar page
                            'url': url,
                            'source': f"Schools ({school_type.title()})",
                            'school_name': school_name,
                            'school_type': school_type,
                            'contact_email': None,
                            'phone_number': None,
                            'interested_count': 0,
                            'attending_count': 0
                        })
                
                elif in_event and ':' in line:
                    # Parse event properties
                    key, value = line.split(':', 1)
                    # Handle properties with parameters (e.g., DTSTART;VALUE=DATE:20240815)
                    key = key.split(';')[0]
                    current_event[key] = value
        
        except Exception as e:
            print(f"[DEBUG] Error parsing Google Calendar ICS: {e}")
        
        return events
    
    def _scrape_google_calendar_html(self, calendar_id: str, school_name: str, school_type: str, location: str, url: str) -> List[Dict[str, Any]]:
        """Fallback: Scrape Google Calendar's public HTML view"""
        events = []
        try:
            # Try the public HTML view of the calendar
            html_url = f"https://calendar.google.com/calendar/embed?src={calendar_id}&mode=AGENDA"
            
            print(f"[DEBUG] Trying Google Calendar HTML view: {html_url[:80]}...")
            response = self.session.get(html_url, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for event elements in the HTML
                event_elements = soup.find_all(['div', 'span'], class_=lambda x: x and 'event' in str(x).lower())
                
                for element in event_elements:
                    text = element.get_text().strip()
                    if text and len(text) > 3 and len(text) < 200:
                        # This is a very basic extraction - Google Calendar HTML is dynamic
                        events.append({
                            'title': text,
                            'date': "Date not specified",
                            'when': "Date not specified",
                            'location': location,
                            'address': school_name,  # Show just the school name
                            'description': f"Google Calendar event from {school_name}",
                            'website': url,  # School's calendar page
                            'url': url,
                            'source': f"Schools ({school_type.title()})",
                            'school_name': school_name,
                            'school_type': school_type,
                            'contact_email': None,
                            'phone_number': None,
                            'interested_count': 0,
                            'attending_count': 0
                        })
                
                print(f"[DEBUG] Extracted {len(events)} events from Google Calendar HTML")
            else:
                print(f"[DEBUG] Google Calendar HTML view returned {response.status_code}")
        
        except Exception as e:
            print(f"[DEBUG] Error scraping Google Calendar HTML: {e}")
        
        return events[:10]  # Limit to 10 events to avoid spam
    
    def _parse_event_element(self, element, school_name: str, school_type: str, location: str, url: str) -> Optional[Dict[str, Any]]:
        """Parse a single event element from HTML"""
        try:
            # Extract title
            title_selectors = [
                # FinalSite calendar system - enhanced selectors
                '.fsCalendarTitle',
                '.fsCalendarLongEventDescription', 
                '.fsCalendarEventTitle',
                '.fsCalendarInfo .fsElement',  # Common FinalSite event info
                '.fsCalendarInfo .fsText',     # FinalSite text elements
                '.fsCalendarInfo a',           # Links within calendar info
                '.fsElementContent',           # FinalSite element content
                '[class*="fsCalendar"] .fsElementContent',
                '[class*="fsCalendar"] a',     # Any links in FinalSite calendar
                
                # Standard selectors
                '.event-title', '.title', 'h1', 'h2', 'h3', 'h4', 
                '.fc-title', '.tribe-events-list-event-title',
                '[class*="title"]', 'a'
            ]
            
            title = None
            for selector in title_selectors:
                title_elem = element.select_one(selector)
                if title_elem:
                    title = title_elem.get_text().strip()
                    if title and len(title) > 3:
                        break
            
            if not title:
                # Fallback: use element text if no specific title found
                title = element.get_text().strip()[:100]  # Limit length
                
                # Debug: Show element structure if we're falling back to raw text
                if len(title) < 50:  # Only debug short/simple elements
                    print(f"[DEBUG] Fallback element HTML: {str(element)[:200]}...")
            
            # Filter out location-only elements that aren't actual events
            location_only_patterns = [
                'my paymentsplus', 'paymentsplus', 'payment plus',
                'general.*gym', 'gymnasium', 'cafeteria', 'auditorium',
                'library', 'parking lot', 'main office'
            ]
            
            title_lower = title.lower()
            if any(pattern in title_lower for pattern in location_only_patterns):
                print(f"[DEBUG] ✗ Skipped location-only element: '{title}'")
                return None
            
            if not title or len(title) < 3:
                return None
            
            # Extract date/time
            date_selectors = [
                # FinalSite calendar system - look for data attributes and spans
                '[data-start-date]',  # FinalSite data attributes
                '[data-date]',
                '.fsCalendarDate',
                '.fsCalendarEventDate',
                
                # Standard selectors
                '.event-date', '.date', '.fc-time', '.tribe-events-event-meta-date',
                '[class*="date"]', '[class*="time"]', 'time', '.datetime'
            ]
            
            event_date = "Date not specified"
            
            # First, try to extract date from the element itself, parent elements, and child elements
            check_elements = [element]
            if element.parent:
                check_elements.append(element.parent)
                if element.parent.parent:
                    check_elements.append(element.parent.parent)
            
            # Also check all child elements (especially <a> tags with data-occur-id)
            for child in element.find_all(['a', 'div', 'span']):
                check_elements.append(child)
            
            for check_elem in check_elements:
                if check_elem is None:
                    continue
                    
                # Check for FinalSite data attributes
                for attr in ['data-start-date', 'data-date', 'data-event-date', 'data-occur-id']:
                    if check_elem.get(attr):
                        attr_value = check_elem.get(attr)
                        if attr == 'data-occur-id':
                            # FinalSite data-occur-id format: "id_2025-08-04T00:00:00Z_2025-08-05T00:00:00Z"
                            date_match = re.search(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)', attr_value)
                            if date_match:
                                event_date = self._format_date_with_timezone(date_match.group(1), 'US/Eastern')
                                break
                        else:
                            event_date = self._format_date(attr_value)
                            break
                
                if event_date != "Date not specified":
                    break
            
            # If no data attributes found, look for date elements
            if event_date == "Date not specified":
                for selector in date_selectors:
                    date_elem = element.select_one(selector)
                    if date_elem:
                        # Try datetime attribute first
                        datetime_attr = date_elem.get('datetime')
                        if datetime_attr:
                            event_date = self._format_date(datetime_attr)
                            break
                        
                        # Try data attributes
                        for attr in ['data-start-date', 'data-date', 'data-occur-id']:
                            if date_elem.get(attr):
                                attr_value = date_elem.get(attr)
                                if attr == 'data-occur-id':
                                    # FinalSite data-occur-id format: "id_2025-08-04T00:00:00Z_2025-08-05T00:00:00Z"
                                    date_match = re.search(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)', attr_value)
                                    if date_match:
                                        event_date = self._format_date_with_timezone(date_match.group(1), 'US/Eastern')
                                        break
                                else:
                                    event_date = self._format_date(attr_value)
                                    break
                        
                        if event_date != "Date not specified":
                            break
                        
                        # Otherwise use text content
                        date_text = date_elem.get_text().strip()
                        if date_text and len(date_text) > 3:
                            event_date = date_text
                            break
            
            # Extract description
            description_selectors = [
                '.event-description', '.description', '.content', '.excerpt',
                '.fc-content', '.tribe-events-list-event-description'
            ]
            
            description = f"{school_type.title()} school event from {school_name}"
            for selector in description_selectors:
                desc_elem = element.select_one(selector)
                if desc_elem:
                    desc_text = desc_elem.get_text().strip()
                    if desc_text and len(desc_text) > 10:
                        description = desc_text[:200]  # Limit length
                        break
            
            # Always use the school's calendar page URL as the website
            # (since school events typically don't have individual detail pages)
            calendar_url = url  # This is the pre-defined calendar page URL
            
            return {
                'title': title,
                'date': event_date,
                'when': event_date,
                'location': location,
                'address': school_name,  # Show just the school name in the School column
                'description': description,
                'website': calendar_url,  # Always the school's calendar page
                'url': calendar_url,      # Same as website for consistency
                'source': f"Schools ({school_type.title()})",
                'school_name': school_name,
                'school_type': school_type,
                'contact_email': None,
                'phone_number': None,
                'interested_count': 0,
                'attending_count': 0
            }
            
        except Exception as e:
            print(f"[DEBUG] Error parsing event element: {e}")
            return None
    
    def _extract_structured_data_events(self, soup: BeautifulSoup, school_name: str, school_type: str, location: str, url: str) -> List[Dict[str, Any]]:
        """Extract events from structured data (JSON-LD, microdata)"""
        events = []
        
        try:
            # Look for JSON-LD structured data
            json_scripts = soup.find_all('script', type='application/ld+json')
            for script in json_scripts:
                try:
                    import json
                    data = json.loads(script.string)
                    
                    # Handle different structured data formats
                    if isinstance(data, list):
                        for item in data:
                            event = self._parse_structured_event(item, school_name, school_type, location, url)
                            if event:
                                events.append(event)
                    elif isinstance(data, dict):
                        event = self._parse_structured_event(data, school_name, school_type, location, url)
                        if event:
                            events.append(event)
                            
                except Exception as e:
                    print(f"[DEBUG] Error parsing JSON-LD: {e}")
                    continue
        
        except Exception as e:
            print(f"[DEBUG] Error extracting structured data: {e}")
        
        return events
    
    def _parse_structured_event(self, data: dict, school_name: str, school_type: str, location: str, url: str) -> Optional[Dict[str, Any]]:
        """Parse a single event from structured data"""
        try:
            # Check if this is an event
            event_type = data.get('@type', '').lower()
            if 'event' not in event_type:
                return None
            
            title = data.get('name') or data.get('headline')
            if not title:
                return None
            
            # Extract date
            start_date = data.get('startDate') or data.get('datePublished')
            event_date = self._format_date(start_date) if start_date else "Date not specified"
            
            # Extract description
            description = data.get('description') or f"{school_type.title()} school event from {school_name}"
            
            # Always use the school's calendar page URL as the website
            calendar_url = url  # This is the pre-defined calendar page URL
            
            return {
                'title': title,
                'date': event_date,
                'when': event_date,
                'location': location,
                'address': school_name,  # Show just the school name in the School column
                'description': description[:200] if description else "",
                'website': calendar_url,  # Always the school's calendar page
                'url': calendar_url,      # Same as website for consistency
                'source': f"Schools ({school_type.title()})",
                'school_name': school_name,
                'school_type': school_type,
                'contact_email': None,
                'phone_number': None,
                'interested_count': 0,
                'attending_count': 0
            }
            
        except Exception as e:
            print(f"[DEBUG] Error parsing structured event: {e}")
            return None
    
    def _extract_text_pattern_events(self, soup: BeautifulSoup, school_name: str, school_type: str, location: str, url: str) -> List[Dict[str, Any]]:
        """Extract events using text pattern matching as fallback"""
        events = []
        
        try:
            # Get all text content
            text_content = soup.get_text()
            
            # Look for date patterns that might indicate events
            date_patterns = [
                r'(\w+\s+\d{1,2},?\s+\d{4})',  # January 15, 2024
                r'(\d{1,2}/\d{1,2}/\d{4})',     # 1/15/2024
                r'(\d{1,2}-\d{1,2}-\d{4})',     # 1-15-2024
            ]
            
            for pattern in date_patterns:
                matches = re.finditer(pattern, text_content, re.IGNORECASE)
                for match in matches:
                    date_str = match.group(1)
                    
                    # Look for event titles around the date
                    start_pos = max(0, match.start() - 100)
                    end_pos = min(len(text_content), match.end() + 100)
                    context = text_content[start_pos:end_pos]
                    
                    # Simple heuristic: look for lines that might be event titles
                    lines = context.split('\n')
                    for line in lines:
                        line = line.strip()
                        if (line and len(line) > 10 and len(line) < 100 and
                            not line.isdigit() and 
                            any(keyword in line.lower() for keyword in ['event', 'meeting', 'conference', 'celebration', 'festival', 'show', 'game', 'performance'])):
                            
                            events.append({
                                'title': line,
                                'date': date_str,
                                'when': date_str,
                                'location': location,
                                'address': school_name,  # Show just the school name
                                'description': f"Text-extracted event from {school_name}",
                                'website': url,  # Pre-defined school calendar page
                                'url': url,      # Same as website
                                'source': f"Schools ({school_type.title()})",
                                'school_name': school_name,
                                'school_type': school_type,
                                'contact_email': None,
                                'phone_number': None,
                                'interested_count': 0,
                                'attending_count': 0
                            })
                            break  # Only take first potential title per date
        
        except Exception as e:
            print(f"[DEBUG] Error in text pattern extraction: {e}")
        
        return events[:5]  # Limit to 5 events to avoid spam
    
    def _debug_calendar_structure(self, soup: BeautifulSoup, school_name: str, url: str) -> None:
        """Debug method to analyze the calendar HTML structure"""
        try:
            print(f"[DEBUG] === Analyzing calendar structure for {school_name} ===")
            
            # Check for common calendar frameworks
            frameworks = {
                'FullCalendar': soup.find_all(class_=lambda x: x and 'fc-' in x),
                'Events Calendar': soup.find_all(class_=lambda x: x and 'tribe-events' in str(x)),
                'Google Calendar': soup.find_all('iframe', src=lambda x: x and 'calendar.google.com' in str(x)),
                'WordPress Events': soup.find_all(class_=lambda x: x and 'event' in str(x).lower()),
            }
            
            for framework, elements in frameworks.items():
                if elements:
                    print(f"[DEBUG] Found {framework} framework: {len(elements)} elements")
            
            # Look for any calendar-related classes
            all_classes = set()
            for element in soup.find_all(class_=True):
                if isinstance(element.get('class'), list):
                    all_classes.update(element.get('class'))
            
            calendar_classes = [cls for cls in all_classes if any(keyword in cls.lower() 
                               for keyword in ['calendar', 'event', 'date', 'schedule', 'day'])]
            
            if calendar_classes:
                print(f"[DEBUG] Calendar-related CSS classes found: {calendar_classes[:10]}")  # Show first 10
            else:
                print(f"[DEBUG] No obvious calendar CSS classes found")
            
            # Look for date patterns in text content
            import re
            text_content = soup.get_text()
            date_patterns = re.findall(r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2}(?:,\s*\d{4})?\b', text_content)
            
            if date_patterns:
                print(f"[DEBUG] Date patterns found in text: {date_patterns[:5]}")  # Show first 5
            else:
                print(f"[DEBUG] No obvious date patterns found in text")
            
            # Look for tables that might contain calendar data
            tables = soup.find_all('table')
            if tables:
                print(f"[DEBUG] Found {len(tables)} table(s) - potential calendar grid")
                for i, table in enumerate(tables[:2]):  # Check first 2 tables
                    rows = table.find_all('tr')
                    print(f"[DEBUG] Table {i+1}: {len(rows)} rows")
            
            # Look for list-based calendars
            lists = soup.find_all(['ul', 'ol'])
            event_lists = [lst for lst in lists if any(keyword in str(lst).lower() 
                          for keyword in ['event', 'calendar', 'schedule'])]
            if event_lists:
                print(f"[DEBUG] Found {len(event_lists)} potential event lists")
            
            # Check for JavaScript that might load calendar data
            scripts = soup.find_all('script')
            calendar_scripts = [script for script in scripts if script.string and 
                               any(keyword in script.string.lower() for keyword in ['calendar', 'event', 'fullcalendar'])]
            if calendar_scripts:
                print(f"[DEBUG] Found {len(calendar_scripts)} calendar-related scripts")
            
            print(f"[DEBUG] === End calendar structure analysis ===")
            
        except Exception as e:
            print(f"[DEBUG] Error in calendar structure analysis: {e}")
    
    def _format_date(self, date_str: str) -> str:
        """Format date string consistently for display and parsing"""
        if not date_str:
            return "Date not specified"
        
        try:
            # Try to parse ISO format (common in Google Calendar feeds)
            if 'T' in date_str or '+' in date_str or 'Z' in date_str:
                try:
                    from dateutil.parser import parse
                    dt = parse(date_str)
                    # Return in a format that our date parser can handle
                    return dt.strftime('%a, %b %d, %Y at %I:%M %p')
                except ImportError:
                    # Fallback without dateutil
                    import re
                    # Extract just the date part from ISO format
                    date_match = re.match(r'(\d{4}-\d{2}-\d{2})', date_str)
                    if date_match:
                        try:
                            dt = datetime.strptime(date_match.group(1), '%Y-%m-%d')
                            return dt.strftime('%a, %b %d, %Y')
                        except ValueError:
                            pass
            
            # Try other common formats
            format_mappings = [
                ('%Y-%m-%d', '%a, %b %d, %Y'),           # 2024-08-15 -> Mon, Aug 15, 2024
                ('%m/%d/%Y', '%a, %b %d, %Y'),           # 8/15/2024 -> Mon, Aug 15, 2024  
                ('%d/%m/%Y', '%a, %b %d, %Y'),           # 15/8/2024 -> Mon, Aug 15, 2024
                ('%B %d, %Y', '%a, %b %d, %Y'),          # August 15, 2024 -> Mon, Aug 15, 2024
                ('%b %d, %Y', '%a, %b %d, %Y'),          # Aug 15, 2024 -> Mon, Aug 15, 2024
                ('%Y%m%d', '%a, %b %d, %Y'),             # 20240815 -> Mon, Aug 15, 2024
            ]
            
            for input_fmt, output_fmt in format_mappings:
                try:
                    dt = datetime.strptime(date_str, input_fmt)
                    return dt.strftime(output_fmt)
                except ValueError:
                    continue
            
            # If we can't parse it, return original but ensure it's clean
            cleaned = date_str.strip()
            if cleaned and cleaned != "Date not specified":
                return cleaned
            
            return "Date not specified"
            
        except Exception as e:
            print(f"[DEBUG] Error formatting date '{date_str}': {e}")
            return date_str
    
    def _format_date_with_timezone(self, date_str: str, target_timezone: str) -> str:
        """Format UTC date string and convert to target timezone"""
        if not date_str:
            return "Date not specified"
        
        try:
            # Parse UTC datetime (e.g., "2025-09-02T11:30:00Z")
            if 'T' in date_str and 'Z' in date_str:
                # Parse as UTC
                dt_utc = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                
                # Check if this is an all-day event (midnight UTC)
                if dt_utc.hour == 0 and dt_utc.minute == 0:
                    # For all-day events, just use the date without timezone conversion
                    # to avoid showing the previous day due to timezone offset
                    return dt_utc.strftime('%a, %b %d, %Y')
                else:
                    # Convert to Eastern Time for timed events
                    import pytz
                    eastern_tz = pytz.timezone('US/Eastern')
                    dt_local = dt_utc.astimezone(eastern_tz)
                    return dt_local.strftime('%a, %b %d, %Y at %I:%M %p')
            else:
                # Fallback to regular formatting
                return self._format_date(date_str)
                
        except Exception as e:
            print(f"[DEBUG] Error formatting date with timezone '{date_str}': {e}")
            # Fallback to regular formatting
            return self._format_date(date_str)
    
    def _deduplicate_events(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate events based on title and date"""
        seen = set()
        unique_events = []
        
        for event in events:
            # Create a key based on normalized title and date
            title = event.get('title', '').strip().lower()
            date = event.get('date', '').strip().lower()
            key = f"{title}|{date}"
            
            if key not in seen:
                seen.add(key)
                unique_events.append(event)
        
        return unique_events
    
    def _filter_events_by_date_range(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter events to only include those in the next 2 weeks (configurable)"""
        filtered_events = []
        
        # Calculate date range
        today = date.today()
        end_date = today + timedelta(days=self.DEFAULT_DAYS_AHEAD)
        
        print(f"[DEBUG] Filtering events from {today} to {end_date} ({self.DEFAULT_DAYS_AHEAD} days ahead)")
        
        for event in events:
            event_date_str = event.get('date', '') or event.get('when', '')
            
            # Try to parse the event date
            parsed_date = self._parse_event_date(event_date_str)
            
            if parsed_date:
                # Check if event is within our date range
                if self.INCLUDE_TODAY:
                    is_in_range = today <= parsed_date <= end_date
                else:
                    is_in_range = today < parsed_date <= end_date
                
                if is_in_range:
                    filtered_events.append(event)
                    print(f"[DEBUG] ✓ Included: '{event.get('title', '')[:40]}...' on {parsed_date}")
                else:
                    print(f"[DEBUG] ✗ Excluded: '{event.get('title', '')[:40]}...' on {parsed_date} (outside range)")
            else:
                # If we can't parse the date, include it but warn
                filtered_events.append(event)
                print(f"[DEBUG] ? Included (unparseable date): '{event.get('title', '')[:40]}...' date='{event_date_str}'")
        
        return filtered_events
    
    def _parse_event_date(self, date_str: str) -> Optional[date]:
        """Parse various date formats to extract the actual date"""
        if not date_str or date_str == "Date not specified":
            return None
        
        try:
            # Remove common prefixes and clean up
            cleaned_date = date_str.strip()
            
            # Handle various date formats
            date_formats = [
                # Standard formats
                '%Y-%m-%d',           # 2024-08-15
                '%m/%d/%Y',           # 8/15/2024
                '%d/%m/%Y',           # 15/8/2024
                '%m-%d-%Y',           # 8-15-2024
                '%B %d, %Y',          # August 15, 2024
                '%b %d, %Y',          # Aug 15, 2024
                '%A, %B %d, %Y',      # Monday, August 15, 2024
                '%a, %b %d, %Y',      # Mon, Aug 15, 2024
                
                # Formats without year (assume current year)
                '%B %d',              # August 15
                '%b %d',              # Aug 15
                '%m/%d',              # 8/15
                '%m-%d',              # 8-15
                
                # Time-inclusive formats (extract date part)
                '%Y-%m-%d %H:%M:%S',  # 2024-08-15 14:30:00
                '%m/%d/%Y %H:%M %p',  # 8/15/2024 2:30 PM
                '%B %d, %Y at %I:%M %p',  # August 15, 2024 at 2:30 PM
                '%a, %b %d at %I:%M %p',  # Mon, Aug 15 at 2:30 PM
            ]
            
            # Try each format
            for fmt in date_formats:
                try:
                    parsed_dt = datetime.strptime(cleaned_date, fmt)
                    
                    # If no year specified, assume current year
                    if parsed_dt.year == 1900:  # Default year from strptime
                        current_year = date.today().year
                        parsed_dt = parsed_dt.replace(year=current_year)
                    
                    return parsed_dt.date()
                    
                except ValueError:
                    continue
            
            # Try parsing with dateutil if available (more flexible)
            try:
                from dateutil.parser import parse as dateutil_parse
                parsed_dt = dateutil_parse(cleaned_date, default=datetime.now())
                return parsed_dt.date()
            except ImportError:
                pass  # dateutil not available
            except Exception:
                pass  # dateutil parsing failed
            
            # Try to extract date patterns with regex
            import re
            
            # Pattern: Month Day, Year or Month Day Year
            month_day_year = re.search(r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2}(?:,?\s*\d{4})?', cleaned_date, re.IGNORECASE)
            if month_day_year:
                date_part = month_day_year.group(0)
                # Add current year if missing
                if not re.search(r'\d{4}', date_part):
                    date_part += f", {date.today().year}"
                
                for fmt in ['%B %d, %Y', '%b %d, %Y']:
                    try:
                        parsed_dt = datetime.strptime(date_part, fmt)
                        return parsed_dt.date()
                    except ValueError:
                        continue
            
            # Pattern: MM/DD/YYYY or MM/DD
            slash_date = re.search(r'\d{1,2}/\d{1,2}(?:/\d{4})?', cleaned_date)
            if slash_date:
                date_part = slash_date.group(0)
                # Add current year if missing
                if date_part.count('/') == 1:
                    date_part += f"/{date.today().year}"
                
                try:
                    parsed_dt = datetime.strptime(date_part, '%m/%d/%Y')
                    return parsed_dt.date()
                except ValueError:
                    pass
            
            print(f"[DEBUG] Could not parse date: '{date_str}'")
            return None
            
        except Exception as e:
            print(f"[DEBUG] Error parsing date '{date_str}': {e}")
            return None

    def _consolidate_recurring_events(self, events):
        """
        Consolidate events with the same title but different dates into single events with date ranges.
        
        For example:
        - "Lunch Visitors Welcome" on Sep 2, 3, 4, 5 → "Lunch Visitors Welcome" (Sep 2-5, 2025)
        - "Yearbook Presale is Open!" on Aug 31, Sep 1, 2 → "Yearbook Presale is Open!" (Aug 31 - Sep 2, 2025)
        """
        if not events:
            return events
        
        # Group events by normalized title and school
        title_groups = {}
        for event in events:
            # Normalize title for grouping (remove emojis, extra spaces, special chars)
            normalized_title = re.sub(r'[^\w\s]', '', event['title'].lower()).strip()
            # Include school in the key to avoid grouping same event across different schools
            group_key = f"{normalized_title}|{event.get('address', '')}"
            
            if group_key not in title_groups:
                title_groups[group_key] = []
            title_groups[group_key].append(event)
        
        consolidated_events = []
        
        for group_key, group_events in title_groups.items():
            if len(group_events) == 1:
                # Single event, no consolidation needed
                consolidated_events.append(group_events[0])
            else:
                # Multiple events with same title - consolidate them
                print(f"[DEBUG] Consolidating {len(group_events)} instances of '{group_events[0]['title']}'")
                
                # Sort events by date
                dated_events = []
                for event in group_events:
                    parsed_date = self._parse_event_date(event.get('when', ''))
                    if parsed_date:
                        dated_events.append((parsed_date, event))
                    else:
                        # Include events with unparseable dates as separate entries
                        consolidated_events.append(event)
                
                if not dated_events:
                    # No parseable dates, add all events separately
                    consolidated_events.extend(group_events)
                    continue
                
                # Sort by date
                dated_events.sort(key=lambda x: x[0])
                
                # Find date ranges (consecutive dates or very close dates)
                date_ranges = []
                current_range = [dated_events[0]]
                
                for i in range(1, len(dated_events)):
                    current_date = dated_events[i][0]
                    last_date = current_range[-1][0]
                    
                    # If dates are within 2 days of each other, consider them part of the same range
                    if (current_date - last_date).days <= 2:
                        current_range.append(dated_events[i])
                    else:
                        # Start a new range
                        date_ranges.append(current_range)
                        current_range = [dated_events[i]]
                
                # Don't forget the last range
                if current_range:
                    date_ranges.append(current_range)
                
                # Create consolidated events for each date range
                for date_range in date_ranges:
                    if len(date_range) == 1:
                        # Single date, use original event
                        consolidated_events.append(date_range[0][1])
                    else:
                        # Multiple dates, create consolidated event
                        first_event = date_range[0][1]
                        start_date = date_range[0][0]
                        end_date = date_range[-1][0]
                        
                        # Format date range
                        if start_date == end_date:
                            date_range_str = start_date.strftime('%a, %b %d, %Y')
                        elif start_date.month == end_date.month:
                            # Same month: Sep 2-5, 2025
                            date_range_str = f"{start_date.strftime('%b %d')}-{end_date.strftime('%d, %Y')}"
                        else:
                            # Different months: Aug 31 - Sep 2, 2025
                            date_range_str = f"{start_date.strftime('%b %d')} - {end_date.strftime('%b %d, %Y')}"
                        
                        # Create consolidated event
                        consolidated_event = first_event.copy()
                        consolidated_event['when'] = date_range_str
                        consolidated_event['title'] = f"{first_event['title']}"
                        consolidated_event['description'] = f"{first_event.get('description', '')} (Recurring event: {len(date_range)} dates)".strip()
                        
                        consolidated_events.append(consolidated_event)
                        print(f"[DEBUG] ✓ Consolidated '{first_event['title']}' → {len(date_range)} dates → '{date_range_str}'")
        
        return consolidated_events

    def __call__(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Implementation of BaseTool interface"""
        location = input_data.get('location', '')
        start_date = input_data.get('start_date')
        end_date = input_data.get('end_date')
        
        return self.execute(location, start_date, end_date)
