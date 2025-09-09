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
                    },
                    {
                        "name": "Snellville Community Church",
                        "url": "https://www.snellvillecc.org/happenings",
                        "custom_selectors": {
                            # Custom scraper needed for complex calendar layout
                            "event_container": ".photogallery-column, .calendar-event",
                            "title": ".caption-title, h3",
                            "date": ".caption-text, .date",
                            "url": ".caption-button, a"
                        }
                    },
                    {
                        "name": "Church on Main",
                        "url": "https://www.churchonmain.net/events",
                        "custom_selectors": {
                            # Squarespace events structure
                            "event_container": "article.eventlist-event",
                            "title": ".eventlist-title-link",
                            "date": ".event-date",
                            "time": ".event-time-localized",
                            "description": ".eventlist-description",
                            "url": ".eventlist-title-link"
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
            
            # Special handling for Snellville Community Church
            if "snellvillecc.org" in church_url:
                return self._scrape_snellville_community_church(church_name, church_url, location, custom_selectors)
            
            # Special handling for Church on Main (Squarespace)
            if "churchonmain.net" in church_url:
                return self._scrape_church_on_main(church_name, church_url, location, custom_selectors)
            
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

    def _scrape_snellville_community_church(self, church_name: str, church_url: str, location: str, selectors: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Custom scraper for Snellville Community Church events"""
        try:
            print(f"[INFO] Snellville Community Church custom scraper for {location}")
            
            response = self.session.get(church_url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            events = []
            
            # Save debug HTML for inspection
            with open("snellville_debug.html", "w", encoding="utf-8") as f:
                f.write(response.text)
            print("Debug HTML saved to snellville_debug.html")
            
            # Look for photo gallery events (like the 55+ Adult Events Calendar)
            photo_gallery_events = soup.select('.photogallery-column')
            print(f"[DEBUG] Found {len(photo_gallery_events)} photo gallery events")
            
            for i, gallery_event in enumerate(photo_gallery_events):
                try:
                    # Extract title from caption
                    title_elem = gallery_event.select_one('.caption-title')
                    if not title_elem:
                        title_elem = gallery_event.select_one('h3')
                    
                    title = title_elem.get_text(strip=True) if title_elem else None
                    if not title:
                        print(f"[DEBUG] Gallery event {i+1}: No title found, skipping")
                        continue
                    
                    # Extract description from caption text
                    desc_elem = gallery_event.select_one('.caption-text')
                    description = None
                    if desc_elem:
                        desc_text = desc_elem.get_text(strip=True)
                        if desc_text:
                            description = desc_text
                    
                    # Try to parse date from title (e.g., "September 2025")
                    event_date = None
                    if title:
                        event_date = self._parse_date_auto(title)
                    
                    # Extract URL from caption button
                    event_url = None
                    url_elem = gallery_event.select_one('.caption-button')
                    if url_elem:
                        event_url = url_elem.get('href')
                        if event_url and not event_url.startswith('http'):
                            event_url = f"https://www.snellvillecc.org{event_url}" if event_url.startswith('/') else event_url
                    
                    print(f"[DEBUG] Gallery Event {i+1}: {title} | Date: {title} | URL: {event_url or 'N/A'}")
                    
                    # Format date for display
                    formatted_date = None
                    if event_date:
                        formatted_date = event_date.strftime("%B %d, %Y")
                    
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
                    print(f"[DEBUG] Failed to parse gallery event {i+1}: {str(e)}")
                    continue
            
            # Look for specific events listed in the happenings section
            # Search for event headings (h3) that contain dates and event names
            event_headings = soup.select('h3')
            print(f"[DEBUG] Found {len(event_headings)} potential event headings")
            
            for heading in event_headings:
                try:
                    heading_text = heading.get_text(strip=True)
                    if not heading_text or len(heading_text) < 5:
                        continue
                    
                    # Look for date patterns in headings (e.g., "Wednesday, September 10 @6 p.m. - 7 p.m.")
                    import re
                    date_patterns = [
                        r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s*(\w+\s+\d+)',
                        r'(\w+\s+\d+)',
                        r'(\d+/\d+)',
                        r'(\w+\s+\d+,\s*\d{4})'
                    ]
                    
                    has_date = False
                    for pattern in date_patterns:
                        if re.search(pattern, heading_text):
                            has_date = True
                            break
                    
                    if not has_date:
                        continue
                    
                    # Try to parse the date from the heading
                    event_date = self._parse_date_auto(heading_text)
                    
                    # Look for the next element which might contain the event title
                    next_elem = heading.find_next_sibling()
                    event_title = None
                    event_url = None
                    
                    # Check if there's a link following this heading
                    if next_elem and next_elem.name == 'a':
                        event_title = next_elem.get_text(strip=True)
                        event_url = next_elem.get('href')
                    elif next_elem:
                        # Look for text content that might be the event title
                        event_title = next_elem.get_text(strip=True)
                        # Look for links within or after this element
                        link_elem = next_elem.select_one('a') or next_elem.find_next('a')
                        if link_elem:
                            event_url = link_elem.get('href')
                    
                    # If no separate title found, use the heading text itself
                    if not event_title:
                        # Try to extract event name from heading (after the date part)
                        if '@' in heading_text:
                            parts = heading_text.split('@')
                            if len(parts) > 1:
                                event_title = parts[1].strip()
                            else:
                                event_title = parts[0].strip()
                        else:
                            event_title = heading_text
                    
                    if event_url and not event_url.startswith('http'):
                        event_url = f"https://www.snellvillecc.org{event_url}" if event_url.startswith('/') else event_url
                    
                    print(f"[DEBUG] Heading Event: {event_title} | Date: {heading_text} | URL: {event_url or 'N/A'}")
                    
                    # Format date for display
                    formatted_date = None
                    if event_date:
                        formatted_date = event_date.strftime("%B %d, %Y")
                    
                    event = {
                        'title': event_title,
                        'date': event_date.isoformat() if event_date else None,
                        'when': formatted_date,
                        'time': None,
                        'description': None,
                        'location': f"{church_name}, {location}",
                        'url': event_url,
                        'source': church_name,
                        'source_type': 'church',
                        'source_url': church_url,
                        'scraped_at': datetime.now().isoformat()
                    }
                    
                    events.append(event)
                    
                except Exception as e:
                    print(f"[DEBUG] Failed to parse heading event: {str(e)}")
                    continue
            
            # Also look for calendar day events in the monthly calendar
            calendar_events = soup.select('[class*="calendar"], td, .day')
            print(f"[DEBUG] Found {len(calendar_events)} potential calendar elements")
            
            # This is a complex calendar structure, so we'll focus on the simpler extraction methods above
            # The calendar view parsing could be added later if needed
            
            # Deduplicate events based on URL and title similarity
            deduplicated_events = []
            seen_urls = set()
            seen_titles = set()
            
            for event in events:
                event_url = event.get('url', '')
                event_title = event.get('title', '').lower().strip()
                
                # Skip if we've seen this URL before
                if event_url and event_url in seen_urls:
                    print(f"[DEBUG] Skipping duplicate URL: {event_url}")
                    continue
                
                # Skip if we've seen a very similar title before
                is_duplicate_title = False
                for seen_title in seen_titles:
                    # Check if titles are very similar (one might be a date, other the actual title)
                    if (event_title in seen_title or seen_title in event_title) and len(event_title) > 5:
                        print(f"[DEBUG] Skipping similar title: '{event_title}' (similar to '{seen_title}')")
                        is_duplicate_title = True
                        break
                
                if is_duplicate_title:
                    continue
                
                # Prefer events that have proper titles (not dates as titles)
                # If title looks like a date, try to find a better version
                if self._looks_like_date(event_title) and event.get('description'):
                    # This event has a date as title and description as actual event name
                    # Look for a better version in remaining events
                    better_event = None
                    description = event.get('description', '').lower().strip()
                    
                    for other_event in events[events.index(event)+1:]:
                        other_title = other_event.get('title', '').lower().strip()
                        other_url = other_event.get('url', '')
                        
                        # If we find an event with the description as title and same URL, prefer it
                        if (other_title == description or description in other_title) and other_url == event_url:
                            print(f"[DEBUG] Found better version: '{other_event.get('title')}' instead of '{event.get('title')}'")
                            better_event = other_event
                            break
                    
                    if better_event:
                        # Use the better event instead
                        if better_event.get('url'):
                            seen_urls.add(better_event.get('url'))
                        seen_titles.add(better_event.get('title', '').lower().strip())
                        deduplicated_events.append(better_event)
                        continue
                
                # Add this event
                if event_url:
                    seen_urls.add(event_url)
                seen_titles.add(event_title)
                deduplicated_events.append(event)
            
            print(f"[INFO] Snellville Community Church custom scraper found {len(events)} events, {len(deduplicated_events)} after deduplication")
            return deduplicated_events
            
        except Exception as e:
            print(f"[ERROR] Snellville Community Church custom scraper failed: {str(e)}")
            return []

    def _scrape_church_on_main(self, church_name: str, church_url: str, location: str, selectors: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Custom scraper for Church on Main events (Squarespace)"""
        try:
            print(f"[INFO] Church on Main custom scraper for {location}")
            
            response = self.session.get(church_url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            events = []
            
            # Save debug HTML for inspection
            with open("church_on_main_debug.html", "w", encoding="utf-8") as f:
                f.write(response.text)
            print("Debug HTML saved to church_on_main_debug.html")
            
            # Look for Squarespace event containers
            event_containers = soup.select('article.eventlist-event')
            print(f"[DEBUG] Found {len(event_containers)} event containers")
            
            for i, event_container in enumerate(event_containers):
                try:
                    # Extract title
                    title_elem = event_container.select_one('.eventlist-title-link')
                    title = title_elem.get_text(strip=True) if title_elem else None
                    
                    if not title:
                        print(f"[DEBUG] Event {i+1}: No title found, skipping")
                        continue
                    
                    # Extract event URL
                    event_url = None
                    if title_elem:
                        event_url = title_elem.get('href')
                        if event_url and not event_url.startswith('http'):
                            event_url = f"https://www.churchonmain.net{event_url}"
                    
                    # Extract date from datetime attribute
                    date_elem = event_container.select_one('.event-date')
                    event_date = None
                    date_text = None
                    
                    if date_elem:
                        # Try to get date from datetime attribute first
                        datetime_attr = date_elem.get('datetime')
                        if datetime_attr:
                            try:
                                # Parse ISO date format (e.g., "2025-09-11")
                                parsed_date = datetime.fromisoformat(datetime_attr)
                                # Localize to Eastern time
                                tz = pytz.timezone("America/New_York")
                                event_date = tz.localize(parsed_date)
                                date_text = datetime_attr
                            except ValueError:
                                pass
                        
                        # If no datetime attr, try text content
                        if not event_date:
                            date_text = date_elem.get_text(strip=True)
                            if date_text:
                                event_date = self._parse_date_auto(date_text)
                    
                    # Extract time information
                    time_elem = event_container.select_one('.event-time-localized')
                    event_time = None
                    if time_elem:
                        time_text = time_elem.get_text(strip=True)
                        # Clean up time text (remove extra spaces and dashes)
                        event_time = ' - '.join([t.strip() for t in time_text.split() if t.strip() and t.strip() != ''])
                    
                    # Extract description from the eventlist-description
                    description = None
                    desc_container = event_container.select_one('.eventlist-description')
                    if desc_container:
                        # Get text from all paragraphs in the description
                        desc_paragraphs = desc_container.select('p')
                        if desc_paragraphs:
                            desc_texts = []
                            for p in desc_paragraphs:
                                p_text = p.get_text(strip=True)
                                if p_text and len(p_text) > 10:  # Skip very short text
                                    desc_texts.append(p_text)
                            if desc_texts:
                                description = ' '.join(desc_texts)[:500]  # Limit length
                    
                    print(f"[DEBUG] Event {i+1}: {title} | Date: {date_text or 'N/A'} | Time: {event_time or 'N/A'} | URL: {event_url or 'N/A'}")
                    
                    # Skip past events - only include today and future events
                    if event_date:
                        today = datetime.now().date()
                        event_date_only = event_date.date()
                        
                        if event_date_only < today:
                            print(f"[DEBUG] Skipping past event: {title} ({event_date_only})")
                            continue
                    
                    # Format date for display
                    formatted_date = None
                    if event_date:
                        formatted_date = event_date.strftime("%B %d, %Y")
                    
                    event = {
                        'title': title,
                        'date': event_date.isoformat() if event_date else None,
                        'when': formatted_date,
                        'time': event_time,
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
                    print(f"[DEBUG] Failed to parse event {i+1}: {str(e)}")
                    continue
            
            print(f"[INFO] Church on Main custom scraper found {len(events)} events")
            return events
            
        except Exception as e:
            print(f"[ERROR] Church on Main custom scraper failed: {str(e)}")
            return []

    def _looks_like_date(self, text: str) -> bool:
        """Check if text looks like a date rather than an event title"""
        import re
        
        # Common date patterns
        date_patterns = [
            r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)',  # Day of week
            r'\d{1,2}/\d{1,2}',  # MM/DD
            r'\d{4}/\d{4}',      # YYYY/YYYY (like "2025/2026")
            r'(January|February|March|April|May|June|July|August|September|October|November|December)',  # Month names
            r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)',  # Short month names
            r'@\d{1,2}',         # Time indicator like "@6"
            r'\d{1,2}\s*(a\.m\.|p\.m\.|am|pm)',  # Time formats
            r'Deadline:'         # Deadline prefix
        ]
        
        text_lower = text.lower()
        
        # If text contains multiple date indicators, it's likely a date
        matches = 0
        for pattern in date_patterns:
            if re.search(pattern, text_lower):
                matches += 1
        
        # If text has 2+ date patterns, it's probably a date/time string
        return matches >= 2

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
                "%m/%d", "%m-%d", "%d/%m", "%d-%m",
                "%B %Y", "%b %Y"  # Added formats for "September 2025" and "Sep 2025"
            ]
            
            # Clean up date text and handle date ranges
            import re
            original_date_text = date_text
            
            # Handle Snellville Community Church specific formats
            # Remove @ symbols and time information for date parsing
            if '@' in date_text:
                # Extract just the date part before @
                date_text = date_text.split('@')[0].strip()
                print(f"[DEBUG] Removed time info: '{original_date_text}' -> '{date_text}'")
            
            # Handle "Deadline:" prefix
            if 'deadline:' in date_text.lower():
                date_text = re.sub(r'deadline:\s*', '', date_text, flags=re.IGNORECASE).strip()
                print(f"[DEBUG] Removed deadline prefix: '{original_date_text}' -> '{date_text}'")
            
            # Handle date ranges by taking the first date
            if '–' in date_text or '—' in date_text or ' - ' in date_text:  # Handle en-dash, em-dash, and regular dash
                # For patterns like "3–5 October 2025", we need to be smarter
                if re.search(r'\d+[–—-]\d+\s+\w+\s+\d{4}', date_text):
                    # Pattern: "3–5 October 2025" -> "3 October 2025"
                    match = re.search(r'(\d+)[–—-]\d+\s+(\w+\s+\d{4})', date_text)
                    if match:
                        date_text = f"{match.group(1)} {match.group(2)}"
                        print(f"[DEBUG] Multi-day event detected: '{original_date_text}' -> using first date: '{date_text}'")
                else:
                    # For patterns like "Wednesday, September 24 - Saturday, September 27"
                    date_parts = re.split(r'[–—]|\s+-\s+', date_text)
                    if len(date_parts) > 1:
                        date_text = date_parts[0].strip()
                        print(f"[DEBUG] Date range detected: '{original_date_text}' -> using first date: '{date_text}'")
            
            # Clean up remaining non-alphanumeric characters except spaces, slashes, commas
            date_text = re.sub(r'[^\w\s/,-]', '', date_text).strip()
            
            # Special handling for month/year only formats (like "September 2025")
            month_year_match = re.match(r'^(\w+)\s+(\d{4})$', date_text)
            if month_year_match:
                # For month/year, assume the 1st of the month
                date_text = f"{month_year_match.group(1)} 1, {month_year_match.group(2)}"
                print(f"[DEBUG] Month/year format: '{original_date_text}' -> '{date_text}'")
            
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
            
            print(f"[DEBUG] Could not parse date: '{date_text}' (cleaned from '{original_date_text}')")
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
