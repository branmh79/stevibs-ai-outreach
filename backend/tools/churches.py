import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
from .base_tool import BaseTool
import re
import time
from datetime import datetime, timedelta, date
import logging
import pytz

class ChurchesTool(BaseTool):
    name = "churches"
    description = "Fetch church events from church website calendars using web scraping with custom selectors"
    
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
        
        # Location to church URLs mapping - super simple format!
        self.location_config = {
            "Snellville": {  # Match the API parameter format
                "churches": [
                    {
                        "name": "12Stone", 
                        "url": "https://12stone.com/events/",
                        "custom_selectors": {
                            "event_container": ".event__overlay",
                            "title": None,  # Will need to extract from parent element
                            "date": None,   # Will need custom logic
                            "location_filter": "Snellville",  # Filter for this campus
                            "campus_selector": ".filter__select option"
                        }
                    },
                    {
                        "name": "Grace", 
                        "url": "https://gracesnellville.churchcenter.com/registrations",
                        "custom_selectors": {
                            # HTML structure: <article class="css-1k2ec0g"><a href="/registrations/events/..."><h3>Title</h3><p>Date</p></a></article>
                            "event_container": "article.css-1k2ec0g",
                            "title": "h3.lh-1\\.333.c-tint0.fs-3.fw-600",  # Escaped dots for CSS selector
                            "date": "p.css-l49wdp",
                            "url": "a"
                        }
                    }
                    
                    # Add more churches here - the tool will auto-detect selectors
                ]
            }
            # TODO: Add other locations as needed
            # "Other City": {
            #     "churches": [...]
            # }
        }
        
        # Common selector patterns to try automatically
        self.common_selectors = [
            # Pattern 1: Generic event containers
            {
                "event_container": ".event",
                "title": ["h1", "h2", "h3", ".title", ".event-title", ".name"],
                "date": [".date", ".event-date", ".when", "time", ".datetime"],
                "time": [".time", ".event-time", ".start-time"],
                "description": [".description", ".content", ".details", "p"],
                "location": [".location", ".where", ".venue"],
                "url": ["a"]
            },
            # Pattern 2: List items
            {
                "event_container": "li",
                "title": ["h1", "h2", "h3", ".title", ".event-title", ".name"],
                "date": [".date", ".event-date", ".when", "time", ".datetime"],
                "time": [".time", ".event-time", ".start-time"],
                "description": [".description", ".content", ".details", "p"],
                "location": [".location", ".where", ".venue"],
                "url": ["a"]
            },
            # Pattern 3: Calendar-style
            {
                "event_container": ".calendar-event",
                "title": ["h1", "h2", "h3", ".title", ".event-title", ".name"],
                "date": [".date", ".event-date", ".when", "time", ".datetime"],
                "time": [".time", ".event-time", ".start-time"],
                "description": [".description", ".content", ".details", "p"],
                "location": [".location", ".where", ".venue"],
                "url": ["a"]
            },
            # Pattern 4: Card-style
            {
                "event_container": ".card",
                "title": ["h1", "h2", "h3", ".title", ".event-title", ".name"],
                "date": [".date", ".event-date", ".when", "time", ".datetime"],
                "time": [".time", ".event-time", ".start-time"],
                "description": [".description", ".content", ".details", "p"],
                "location": [".location", ".where", ".venue"],
                "url": ["a"]
            },
            # Pattern 5: Generic containers with event keywords
            {
                "event_container": "[class*='event']",
                "title": ["h1", "h2", "h3", ".title", ".event-title", ".name"],
                "date": [".date", ".event-date", ".when", "time", ".datetime"],
                "time": [".time", ".event-time", ".start-time"],
                "description": [".description", ".content", ".details", "p"],
                "location": [".location", ".where", ".venue"],
                "url": ["a"]
            }
        ]
    
    def _normalize_location(self, location: str) -> str:
        """Normalize location string to match our configuration keys"""
        # Remove extra spaces and decode URL encoding
        location = location.replace('+', ' ').strip()
        
        # Try the location as-is first
        if location in self.location_config:
            return location
        
        # Try common variations
        variations = [
            location,  # Original
            location.split(',')[0].strip(),  # Just city name (e.g., "Snellville, GA" -> "Snellville")
            f"{location.split(',')[0].strip()}, GA"  # Add GA if missing
        ]
        
        for variation in variations:
            if variation in self.location_config:
                print(f"[DEBUG] Location '{location}' matched config key '{variation}'")
                return variation
        
        # If no match, return the first variation (just city name)
        normalized = location.split(',')[0].strip()
        print(f"[DEBUG] Location '{location}' normalized to '{normalized}' (no config match)")
        return normalized
    
    def execute(self, location: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, Any]:
        """Execute the church events search using web scraping with custom selectors"""
        try:
            print(f"[INFO] Starting church events search for location: {location}")
            
            # Normalize location - try multiple formats
            normalized_location = self._normalize_location(location)
            church_config = self.location_config.get(normalized_location, {})
            
            if not church_config or not church_config.get("churches"):
                print(f"[INFO] No church configuration found for location: {location} (normalized: {normalized_location})")
                return {
                    'success': True,
                    'events': [],
                    'message': f"No church URLs configured for {location}"
                }
            
            all_events = []
            churches = church_config["churches"]
            
            print(f"[INFO] Processing {len(churches)} church(es) for {location}")
            
            for i, church_config in enumerate(churches):
                try:
                    church_name = church_config.get("name", f"Church {i+1}")
                    church_url = church_config.get("url")
                    
                    if not church_url:
                        print(f"[WARNING] No URL configured for {church_name}")
                        continue
                    
                    print(f"[INFO] Scraping church {i+1}/{len(churches)}: {church_name} - {church_url}")
                    
                    # Check if this church has custom selectors
                    if church_config.get("custom_selectors"):
                        print(f"[INFO] Using custom selectors for {church_name}")
                        events = self._scrape_church_calendar_custom(church_config, location)
                    else:
                        print(f"[INFO] Using auto-detection for {church_name}")
                        events = self._scrape_church_calendar_auto(church_name, church_url, location)
                    
                    all_events.extend(events)
                    print(f"[INFO] Found {len(events)} events from {church_name}")
                    
                    # Be respectful with rate limiting
                    if i < len(churches) - 1:  # Don't sleep after the last request
                        time.sleep(1)
                        
                except Exception as e:
                    church_name = church_config.get("name", f"Church {i+1}")
                    print(f"[ERROR] Failed to scrape {church_name}: {str(e)}")
                    continue
            
            # Filter events by date if specified
            if start_date or end_date:
                all_events = self._filter_events_by_date(all_events, start_date, end_date)
            
            print(f"[INFO] Total church events found: {len(all_events)}")
            
            return {
                'success': True,
                'events': all_events,
                'total_churches': len(churches),
                'location': location
            }
            
        except Exception as e:
            print(f"[ERROR] Church events search failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'events': []
            }
    
    def _scrape_church_calendar_custom(self, church_config: Dict[str, Any], location: str) -> List[Dict[str, Any]]:
        """Handle complex church sites with custom scraping logic"""
        try:
            church_name = church_config.get("name", "Unknown Church")
            church_url = church_config.get("url")
            custom_selectors = church_config.get("custom_selectors", {})
            
            print(f"[INFO] Custom scraping for {church_name}")
            
            # Special handling for 12Stone
            if "12stone.com" in church_url:
                return self._scrape_12stone(church_name, church_url, location, custom_selectors)
            
            # Special handling for Grace Snellville
            if "gracesnellville.churchcenter.com" in church_url:
                import asyncio
                import threading
                
                # Use a separate thread to run the async Playwright code
                def run_async_scraper():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        return loop.run_until_complete(self._scrape_grace_snellville(church_name, church_url, location, custom_selectors))
                    finally:
                        loop.close()
                
                result_container = [None]
                exception_container = [None]
                
                def thread_target():
                    try:
                        result_container[0] = run_async_scraper()
                    except Exception as e:
                        exception_container[0] = e
                
                thread = threading.Thread(target=thread_target)
                thread.start()
                thread.join()
                
                if exception_container[0]:
                    raise exception_container[0]
                
                return result_container[0] or []
            
            # Add other custom church handlers here as needed
            print(f"[WARNING] No custom handler for {church_name}")
            return []
            
        except Exception as e:
            print(f"[ERROR] Custom scraping failed for {church_name}: {str(e)}")
            return []
    
    def _scrape_12stone(self, church_name: str, church_url: str, location: str, selectors: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Custom scraper for 12Stone church events"""
        try:
            print(f"[INFO] 12Stone custom scraper for {location}")
            
            # Normalize location for mapping (remove state suffix)
            clean_location = location.split(',')[0].strip()
            
            # Map location to 12Stone location IDs
            location_mapping = {
                "Snellville": "7",
                "Athens": "0", 
                "Braselton": "1",
                "Buford": "2",
                "Flowery Branch": "3",
                "Hamilton Mill": "4",
                "Jackson County": "5",
                "Lawrenceville": "6",
                "Sugarloaf": "8",
                "Gas South Convention Center": "9"
            }
            
            target_location_id = location_mapping.get(clean_location)
            if not target_location_id:
                print(f"[WARNING] Unknown location for 12Stone: {location} (cleaned: {clean_location})")
                return []
            
            print(f"[DEBUG] Looking for events with location ID '{target_location_id}' or '0' (All Locations)")
            
            response = self.session.get(church_url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            events = []
            
            # Look for event containers with data-locations attribute
            event_containers = soup.select(".swiper-slide.event.js-event")
            print(f"[DEBUG] Found {len(event_containers)} total event containers")
            
            for event_container in event_containers:
                try:
                    # Check if this event is for our target location or all locations
                    data_locations = event_container.get('data-locations', '')
                    if not data_locations:
                        continue
                    
                    location_ids = data_locations.split(',')
                    # Check if event is for our target location (e.g., "7" for Snellville) or "0" (All Locations)
                    if target_location_id not in location_ids and "0" not in location_ids:
                        print(f"[DEBUG] Skipping event - locations: {data_locations} (need {target_location_id} or 0)")
                        continue
                    
                    print(f"[DEBUG] Event matches location filter - locations: {data_locations}")
                    
                    # Find the event overlay link within this container
                    overlay = event_container.select_one(".event__overlay")
                    if not overlay:
                        continue
                    
                    # Extract event URL
                    event_url = overlay.get('href')
                    if not event_url:
                        continue
                    
                    # Make absolute URL
                    if event_url.startswith('/'):
                        event_url = f"https://12stone.com{event_url}"
                    
                    # Extract title directly from the container
                    title_elem = event_container.select_one('.event__title')
                    title = title_elem.get_text(strip=True) if title_elem else "Event"
                    
                    # Extract date directly from the container
                    date_elem = event_container.select_one('.event__date span')
                    event_date = None
                    if date_elem:
                        date_text = date_elem.get_text(strip=True)
                        if date_text:
                            event_date = self._parse_date_auto(date_text)
                    
                    # Extract location info from the container
                    location_elem = event_container.select_one('.event__location')
                    event_location_text = location_elem.get_text(strip=True) if location_elem else "All Locations"
                    
                    print(f"[DEBUG] Event: {title} | Date: {date_text if date_elem else 'N/A'} | Location: {event_location_text}")
                    
                    # Try to fetch additional details from the individual event page
                    description = None
                    try:
                        print(f"[DEBUG] Fetching event details from: {event_url}")
                        event_response = self.session.get(event_url, timeout=5)
                        event_response.raise_for_status()
                        event_soup = BeautifulSoup(event_response.content, 'html.parser')
                        
                        # Extract description from meta description
                        meta_desc = event_soup.select_one('meta[name="description"]')
                        if meta_desc:
                            description = meta_desc.get('content', '').strip()
                        
                    except Exception as e:
                        print(f"[DEBUG] Failed to fetch event details for {event_url}: {str(e)}")
                        description = None
                    
                    # Format date for display (e.g., "September 7, 2025")
                    formatted_date = None
                    if event_date:
                        formatted_date = event_date.strftime("%B %d, %Y")
                    
                    event = {
                        'title': title,
                        'date': event_date.isoformat() if event_date else None,  # Keep ISO for backend processing
                        'when': formatted_date,  # User-friendly format for frontend
                        'time': None,
                        'description': description,
                        'location': f"{church_name}, {location} ({event_location_text})",
                        'url': event_url,
                        'source': church_name,
                        'source_type': 'church',
                        'source_url': church_url,
                        'scraped_at': datetime.now().isoformat()
                    }
                    
                    events.append(event)
                    
                except Exception as e:
                    print(f"[DEBUG] Failed to parse event container: {str(e)}")
                    continue
            
            print(f"[INFO] 12Stone custom scraper found {len(events)} events")
            return events
            
        except Exception as e:
            print(f"[ERROR] 12Stone custom scraper failed: {str(e)}")
            return []

    async def _scrape_grace_snellville(self, church_name: str, church_url: str, location: str, selectors: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Custom scraper for Grace Snellville church events using Playwright"""
        try:
            print(f"[INFO] Grace Snellville custom scraper for {location} (using Playwright)")
            
            from playwright.async_api import async_playwright
            
            events = []
            
            async with async_playwright() as p:
                # Launch browser in headless mode
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                )
                page = await context.new_page()
                
                try:
                    print(f"[DEBUG] Loading page: {church_url}")
                    await page.goto(church_url, wait_until='networkidle', timeout=30000)
                    
                    # Wait for events to load - look for the event containers
                    try:
                        print(f"[DEBUG] Waiting for event containers to load...")
                        await page.wait_for_selector(selectors.get("event_container", "article.css-1k2ec0g"), timeout=15000)
                    except:
                        print(f"[DEBUG] Event containers didn't load with specific selector, trying general selectors...")
                        # Try waiting for any common event indicators
                        try:
                            await page.wait_for_selector("article, [class*='event'], a[href*='registrations/events']", timeout=10000)
                        except:
                            print(f"[WARNING] No event containers found, proceeding with current page content")
                    
                    # Get the page content after JavaScript has loaded
                    content = await page.content()
                    soup = BeautifulSoup(content, 'html.parser')
                    
                    # Try multiple selector patterns for event containers
                    possible_selectors = [
                        selectors.get("event_container", "article.css-1k2ec0g"),
                        "article",
                        "[class*='css-1k2ec0g']",
                        "a[href*='/registrations/events/']",
                        "[class*='event']",
                        "div[class*='card']"
                    ]
                    
                    event_containers = []
                    for selector in possible_selectors:
                        event_containers = soup.select(selector)
                        if event_containers:
                            print(f"[DEBUG] Found {len(event_containers)} containers with selector: {selector}")
                            break
                    
                    if not event_containers:
                        print(f"[WARNING] No event containers found with any selector")
                        # Save debug HTML
                        with open("grace_debug_playwright.html", "w", encoding="utf-8") as f:
                            f.write(content)
                        print("Debug HTML saved to grace_debug_playwright.html")
                        return []
                    
                    print(f"[DEBUG] Processing {len(event_containers)} event containers")
                    
                    for i, event_container in enumerate(event_containers):
                        try:
                            # Extract title - try multiple approaches
                            title = None
                            title_selectors = [
                                selectors.get("title", "h3.lh-1\\.333.c-tint0.fs-3.fw-600"),
                                "h3", "h2", "h1", ".title", "[class*='title']"
                            ]
                            
                            for title_selector in title_selectors:
                                title_elem = event_container.select_one(title_selector)
                                if title_elem:
                                    title = title_elem.get_text(strip=True)
                                    if title:
                                        break
                            
                            if not title:
                                # Try getting title from text content
                                text_content = event_container.get_text(strip=True)
                                if text_content and len(text_content) < 200:  # Reasonable title length
                                    title = text_content.split('\n')[0].strip()
                            
                            if not title or len(title) < 3:
                                print(f"[DEBUG] Skipping container {i+1} - no valid title found")
                                continue
                            
                            # Extract date - try multiple approaches
                            event_date = None
                            date_text = None
                            date_selectors = [
                                selectors.get("date", "p.css-l49wdp"),
                                "p", ".date", "[class*='date']", "time"
                            ]
                            
                            for date_selector in date_selectors:
                                date_elem = event_container.select_one(date_selector)
                                if date_elem:
                                    date_text = date_elem.get_text(strip=True)
                                    if date_text and any(month in date_text.lower() for month in ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']):
                                        event_date = self._parse_date_auto(date_text)
                                        if event_date:
                                            break
                            
                            # Extract event URL
                            event_url = None
                            url_elem = event_container.select_one("a")
                            if url_elem:
                                event_url = url_elem.get('href')
                                if event_url and event_url.startswith('/'):
                                    # Make absolute URL
                                    base_url = 'https://gracesnellville.churchcenter.com'
                                    event_url = f"{base_url}{event_url}"
                            elif event_container.name == 'a':
                                # The container itself is an anchor
                                event_url = event_container.get('href')
                                if event_url and event_url.startswith('/'):
                                    base_url = 'https://gracesnellville.churchcenter.com'
                                    event_url = f"{base_url}{event_url}"
                            
                            print(f"[DEBUG] Event {i+1}: {title} | Date: {date_text or 'N/A'} | URL: {event_url or 'N/A'}")
                            
                            # Format date for display
                            formatted_date = None
                            if event_date:
                                formatted_date = event_date.strftime("%B %d, %Y")
                            
                            # Try to get description from the current page content
                            description = None
                            desc_candidates = event_container.select('p, div, span')
                            for candidate in desc_candidates:
                                text = candidate.get_text(strip=True)
                                if text and text != title and text != date_text and len(text) > 20:
                                    description = text[:500]  # Limit length
                                    break
                            
                            event = {
                                'title': title,
                                'date': event_date.isoformat() if event_date else None,
                                'when': formatted_date,
                                'time': None,
                                'description': description,
                                'location': f"{church_name}, {location}",
                                'url': event_url,
                                'source': church_name,
                                'source_type': 'church',
                                'source_url': church_url,
                                'scraped_at': datetime.now().isoformat()
                            }
                            
                            events.append(event)
                            
                        except Exception as e:
                            print(f"[DEBUG] Failed to parse event container {i+1}: {str(e)}")
                            continue
                    
                finally:
                    await browser.close()
            
            print(f"[INFO] Grace Snellville custom scraper found {len(events)} events")
            return events
            
        except Exception as e:
            print(f"[ERROR] Grace Snellville custom scraper failed: {str(e)}")
            return []

    def _scrape_church_calendar_auto(self, church_name: str, church_url: str, location: str) -> List[Dict[str, Any]]:
        """Auto-detect selectors and scrape events from a church website"""
        try:
            print(f"[INFO] Auto-detecting selectors for {church_name} at {church_url}")
            
            response = self.session.get(church_url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            events = []
            
            # Try each common selector pattern
            for pattern_idx, pattern in enumerate(self.common_selectors):
                print(f"[DEBUG] Trying pattern {pattern_idx + 1}: {pattern['event_container']}")
                
                event_elements = soup.select(pattern["event_container"])
                
                if not event_elements:
                    print(f"[DEBUG] Pattern {pattern_idx + 1}: No elements found with {pattern['event_container']}")
                    continue
                
                print(f"[DEBUG] Pattern {pattern_idx + 1}: Found {len(event_elements)} potential events")
                
                # Try to extract events using this pattern
                pattern_events = []
                for event_element in event_elements[:5]:  # Test first 5 elements
                    event_data = self._extract_event_data_auto(event_element, pattern, church_name, location, church_url)
                    if event_data and event_data.get('title'):  # Must have at least a title
                        pattern_events.append(event_data)
                
                if pattern_events:
                    print(f"[SUCCESS] Pattern {pattern_idx + 1} worked! Found {len(pattern_events)} events")
                    # Use this pattern for all elements
                    all_pattern_events = []
                    for event_element in event_elements:
                        event_data = self._extract_event_data_auto(event_element, pattern, church_name, location, church_url)
                        if event_data and event_data.get('title'):
                            all_pattern_events.append(event_data)
                    return all_pattern_events
                else:
                    print(f"[DEBUG] Pattern {pattern_idx + 1}: No valid events extracted")
            
            print(f"[WARNING] No selector patterns worked for {church_name}")
            return []
            
        except Exception as e:
            print(f"[ERROR] Auto-detection failed for {church_name}: {str(e)}")
            return []
    
    def _extract_event_data_auto(self, event_element, pattern: Dict[str, Any], church_name: str, 
                                location: str, base_url: str) -> Optional[Dict[str, Any]]:
        """Extract event data using auto-detected selectors"""
        try:
            # Helper function to try multiple selectors
            def try_selectors(selectors_list, element):
                for selector in selectors_list:
                    try:
                        found = element.select_one(selector)
                        if found and found.get_text(strip=True):
                            return found.get_text(strip=True)
                    except:
                        continue
                return None
            
            # Extract title (required)
            title = try_selectors(pattern["title"], event_element)
            if not title:
                return None
            
            # Extract date (try to find any date-like text)
            date_text = try_selectors(pattern["date"], event_element)
            event_date = None
            if date_text:
                event_date = self._parse_date_auto(date_text)
            
            # Extract time (optional)
            event_time = try_selectors(pattern.get("time", []), event_element)
            
            # Extract description (optional)
            description = try_selectors(pattern.get("description", []), event_element)
            
            # Extract location (optional)
            event_location = try_selectors(pattern.get("location", []), event_element)
            
            # Extract URL (optional)
            event_url = None
            url_selectors = pattern.get("url", [])
            for selector in url_selectors:
                try:
                    url_element = event_element.select_one(selector)
                    if url_element and url_element.get('href'):
                        event_url = url_element.get('href')
                        # Make relative URLs absolute
                        if event_url and not event_url.startswith('http'):
                            from urllib.parse import urljoin
                            event_url = urljoin(base_url, event_url)
                        break
                except:
                    continue
            
            # Format date for display (e.g., "September 7, 2025")
            formatted_date = None
            if event_date:
                formatted_date = event_date.strftime("%B %d, %Y")
            
            # Build event object
            event = {
                'title': title,
                'date': event_date.isoformat() if event_date else None,  # Keep ISO for backend processing
                'when': formatted_date,  # User-friendly format for frontend
                'time': event_time,
                'description': description,
                'location': event_location or f"{church_name}, {location}",
                'url': event_url,
                'source': church_name,
                'source_type': 'church',
                'source_url': base_url,
                'scraped_at': datetime.now().isoformat()
            }
            
            return event
            
        except Exception as e:
            print(f"[ERROR] Failed to extract event data: {str(e)}")
            return None
    
    def _parse_date_auto(self, date_text: str) -> Optional[datetime]:
        """Parse date string with multiple format attempts"""
        try:
            # Common date formats to try
            formats = [
                "%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y", "%d/%m/%Y",
                "%B %d, %Y", "%b %d, %Y", "%A, %B %d, %Y", "%A, %b %d, %Y",
                "%d %B %Y", "%d %b %Y",  # Added formats for "9 November 2025" and "9 Nov 2025"
                "%B %d", "%b %d", "%A, %B %d", "%A, %b %d",
                "%d %B", "%d %b",  # Added formats for "9 November" and "9 Nov"
                "%m/%d", "%m-%d", "%d/%m", "%d-%m"
            ]
            
            # Clean up date text and handle date ranges
            import re
            original_date_text = date_text
            
            # Handle date ranges by taking the first date
            if '–' in date_text or '—' in date_text:  # Handle en-dash and em-dash (but not regular dash to avoid splitting "2025-26")
                # For patterns like "3–5 October 2025", we need to be smarter
                if re.search(r'\d+[–—]\d+\s+\w+\s+\d{4}', date_text):
                    # Pattern: "3–5 October 2025" -> "3 October 2025"
                    match = re.search(r'(\d+)[–—]\d+\s+(\w+\s+\d{4})', date_text)
                    if match:
                        date_text = f"{match.group(1)} {match.group(2)}"
                        print(f"[DEBUG] Multi-day event detected: '{original_date_text}' -> using first date: '{date_text}'")
                else:
                    # For patterns like "20 August 2025 – 25 March 2026"
                    date_parts = re.split(r'[–—]', date_text)
                    if len(date_parts) > 1:
                        date_text = date_parts[0].strip()
                        print(f"[DEBUG] Date range detected: '{original_date_text}' -> using first date: '{date_text}'")
            
            # Clean up remaining non-alphanumeric characters except spaces, slashes, commas
            date_text = re.sub(r'[^\w\s/,-]', '', date_text).strip()
            
            for fmt in formats:
                try:
                    parsed_date = datetime.strptime(date_text, fmt)
                    # If no year, assume current year
                    if parsed_date.year == 1900:
                        parsed_date = parsed_date.replace(year=datetime.now().year)
                    
                    # Localize to Eastern time (most churches in GA)
                    tz = pytz.timezone("America/New_York")
                    return tz.localize(parsed_date)
                except ValueError:
                    continue
            
            print(f"[DEBUG] Could not parse date: '{date_text}'")
            return None
            
        except Exception as e:
            print(f"[ERROR] Date parsing failed: {str(e)}")
            return None

    def _scrape_church_calendar(self, church_config: Dict[str, Any], location: str) -> List[Dict[str, Any]]:
        """Scrape events from a single church using custom selectors"""
        try:
            church_name = church_config.get("name", "Unknown Church")
            url = church_config.get("url")
            selectors = church_config.get("selectors", {})
            date_format = church_config.get("date_format", "%Y-%m-%d")
            timezone_str = church_config.get("timezone", "America/New_York")
            
            if not url or not selectors:
                print(f"[WARNING] Missing URL or selectors for {church_name}")
                return []
            
            print(f"[INFO] Fetching {church_name} calendar from: {url}")
            
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            events = []
            
            # Find event containers using the specified selector
            event_container_selector = selectors.get("event_container")
            if not event_container_selector:
                print(f"[ERROR] No event_container selector specified for {church_name}")
                return []
            
            event_elements = soup.select(event_container_selector)
            print(f"[INFO] Found {len(event_elements)} potential events for {church_name}")
            
            for event_element in event_elements:
                try:
                    event_data = self._extract_event_data(event_element, selectors, church_name, date_format, timezone_str, location)
                    if event_data:
                        events.append(event_data)
                except Exception as e:
                    print(f"[WARNING] Failed to parse event from {church_name}: {str(e)}")
                    continue
            
            return events
            
        except Exception as e:
            print(f"[ERROR] Failed to scrape {church_name}: {str(e)}")
            return []
    
    def _extract_event_data(self, event_element, selectors: Dict[str, str], church_name: str, 
                           date_format: str, timezone_str: str, location: str) -> Optional[Dict[str, Any]]:
        """Extract event data from a single event element using custom selectors"""
        try:
            # Extract title
            title_selector = selectors.get("title")
            title = None
            if title_selector:
                title_element = event_element.select_one(title_selector)
                if title_element:
                    title = title_element.get_text(strip=True)
            
            if not title:
                print(f"[WARNING] No title found for event in {church_name}")
                return None
            
            # Extract date
            date_selector = selectors.get("date")
            event_date = None
            if date_selector:
                date_element = event_element.select_one(date_selector)
                if date_element:
                    date_text = date_element.get_text(strip=True)
                    event_date = self._parse_date(date_text, date_format, timezone_str)
            
            # Extract time (optional)
            time_selector = selectors.get("time")
            event_time = None
            if time_selector:
                time_element = event_element.select_one(time_selector)
                if time_element:
                    event_time = time_element.get_text(strip=True)
            
            # Extract description (optional)
            description_selector = selectors.get("description")
            description = None
            if description_selector:
                desc_element = event_element.select_one(description_selector)
                if desc_element:
                    description = desc_element.get_text(strip=True)
            
            # Extract location (optional)
            location_selector = selectors.get("location")
            event_location = None
            if location_selector:
                loc_element = event_element.select_one(location_selector)
                if loc_element:
                    event_location = loc_element.get_text(strip=True)
            
            # Extract URL (optional)
            url_selector = selectors.get("url")
            event_url = None
            if url_selector:
                url_element = event_element.select_one(url_selector)
                if url_element and url_element.get('href'):
                    event_url = url_element.get('href')
                    # Make relative URLs absolute
                    if event_url and not event_url.startswith('http'):
                        from urllib.parse import urljoin
                        base_url = '/'.join(selectors.get('base_url', '').split('/')[:3])
                        event_url = urljoin(base_url, event_url)
            
            # Build event object
            event = {
                'title': title,
                'date': event_date.isoformat() if event_date else None,
                'time': event_time,
                'description': description,
                'location': event_location or f"{church_name}, {location}",
                'url': event_url,
                'source': church_name,
                'source_type': 'church',
                'source_url': selectors.get('base_url', ''),
                'scraped_at': datetime.now().isoformat()
            }
            
            return event
            
        except Exception as e:
            print(f"[ERROR] Failed to extract event data: {str(e)}")
            return None
    
    def _parse_date(self, date_text: str, date_format: str, timezone_str: str) -> Optional[datetime]:
        """Parse date string into datetime object"""
        try:
            # Try the specified format first
            try:
                parsed_date = datetime.strptime(date_text, date_format)
                tz = pytz.timezone(timezone_str)
                return tz.localize(parsed_date)
            except ValueError:
                pass
            
            # Try common date formats as fallbacks
            common_formats = [
                "%Y-%m-%d",
                "%m/%d/%Y",
                "%m-%d-%Y",
                "%B %d, %Y",
                "%b %d, %Y",
                "%A, %B %d, %Y",
                "%A, %b %d, %Y"
            ]
            
            for fmt in common_formats:
                try:
                    parsed_date = datetime.strptime(date_text, fmt)
                    tz = pytz.timezone(timezone_str)
                    return tz.localize(parsed_date)
                except ValueError:
                    continue
            
            print(f"[WARNING] Could not parse date: {date_text}")
            return None
            
        except Exception as e:
            print(f"[ERROR] Date parsing failed: {str(e)}")
            return None
    
    def _filter_events_by_date(self, events: List[Dict[str, Any]], start_date: Optional[str] = None, 
                              end_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """Filter events by date range"""
        try:
            filtered_events = []
            
            # Set default date range if not provided
            if not start_date:
                start_date = datetime.now().date().isoformat() if self.INCLUDE_TODAY else (datetime.now().date() + timedelta(days=1)).isoformat()
            
            if not end_date:
                end_date = (datetime.now().date() + timedelta(days=self.DEFAULT_DAYS_AHEAD)).isoformat()
            
            start_dt = datetime.fromisoformat(start_date).date()
            end_dt = datetime.fromisoformat(end_date).date()
            
            for event in events:
                event_date_str = event.get('date')
                if not event_date_str:
                    continue
                
                try:
                    event_date = datetime.fromisoformat(event_date_str).date()
                    if start_dt <= event_date <= end_dt:
                        filtered_events.append(event)
                except ValueError:
                    print(f"[WARNING] Invalid date format in event: {event_date_str}")
                    continue
            
            return filtered_events
            
        except Exception as e:
            print(f"[ERROR] Date filtering failed: {str(e)}")
            return events  # Return unfiltered events on error
    
    def add_church(self, location: str, name: str, url: str) -> bool:
        """Add a new church configuration at runtime - simple format!"""
        try:
            if location not in self.location_config:
                self.location_config[location] = {"churches": []}
            
            church_config = {"name": name, "url": url}
            self.location_config[location]["churches"].append(church_config)
            print(f"[INFO] Added church configuration for {name} in {location}")
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to add church configuration: {str(e)}")
            return False
    
    def get_church_configs(self, location: str) -> List[Dict[str, Any]]:
        """Get all church configurations for a location"""
        return self.location_config.get(location, {}).get("churches", [])
    
    def __call__(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """BaseTool interface compatibility"""
        location = input_data.get("location", "Snellville")
        start_date = input_data.get("start_date")
        end_date = input_data.get("end_date")
        
        return self.execute(location, start_date, end_date)
