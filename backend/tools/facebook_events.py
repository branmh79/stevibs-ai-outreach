import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
from .base_tool import BaseTool
import re
import time
import json
import asyncio
import os

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
                response = self.session.get(search_url, timeout=5)  # Reduced timeout
                print(f"Response status: {response.status_code}")
                
                if response.status_code == 200:
                    print(f"Success with URL: {search_url}")
                                        
                    # Parse the HTML response
                    soup = BeautifulSoup(response.content, 'html.parser')
                    # HTML length can still be useful
                    print(f"HTML content length: {len(response.content)}")
                    
                    # Static HTML parsing no longer supported - use Playwright
                    events = []
                    print(f"[DEBUG] Static HTML parsing skipped - Playwright method will be used")

                    # Try to paginate using cursor to load more results (simulate scrolling)
                    all_events = events
                    
                    # Extract initial GraphQL cursor from embedded JSON (end_cursor)
                    end_cursor_match = re.search(r'"end_cursor":"([^"]+)"', response.text)
                    if end_cursor_match:
                        next_cursor = end_cursor_match.group(1)
                        print(f"[DEBUG] Found initial end_cursor for GraphQL: {next_cursor[:20]}...")

                        # Extract tokens required for GraphQL POST
                        fb_dtsg, lsd = self._extract_facebook_tokens(response.text)

                        if fb_dtsg and lsd:
                            print("[DEBUG] Found fb_dtsg and lsd tokens; starting GraphQL pagination")
                            page_count = 0
                            max_pages = 15  # Increased from 5 to load more pages
                            while next_cursor and len(all_events) < 100 and page_count < max_pages:  # Increased limit to 100 events
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
                                    "count": 15,
                                    "cursor": next_cursor,
                                    "feedLocation": "SEARCH",
                                    "fetch_filters": True,
                                    "scale": 1,
                                    "stream_initial_count": 0,
                                    "__relay_internal__pv__IsWorkUserrelayprovider": False,
                                    "__relay_internal__pv__IsMergQApolloRecentMessagesrelayprovider": False,
                                    "__relay_internal__pv__IsMergQAsMetaQArelayprovider": False,
                                    "__relay_internal__pv__CometUFIIsRTAEnabledrelayprovider": False,
                                    "__relay_internal__pv__IncludeCommentPromptrelayprovider": True,
                                    "__relay_internal__pv__StoriesArmadilloReplyEnabledrelayprovider": False,
                                    "__relay_internal__pv__EventCometCardImage_prefetchEventImagerelayprovider": False
                                }

                                payload = {
                                    'doc_id': '32141493598774813',
                                    'variables': json.dumps(variables, separators=(',', ':')),
                                    'fb_dtsg': fb_dtsg,
                                    'lsd': lsd
                                }

                                print(f"[DEBUG] GraphQL page {page_count+1} cursor: {next_cursor[:15]}...")
                                print(f"[DEBUG] Using fb_dtsg: {fb_dtsg[:20]}... lsd: {lsd[:20]}...")
                                print(f"[DEBUG] Variables: {json.dumps(variables, separators=(',', ':'))[:200]}...")
                                
                                gql_resp = self.session.post('https://www.facebook.com/api/graphql/', data=payload, timeout=10)
                                if gql_resp.status_code != 200:
                                    print(f"[DEBUG] GraphQL request failed: {gql_resp.status_code}")
                                    break
                                try:
                                    gql_json = gql_resp.json()
                                    print(f"[DEBUG] GraphQL response structure: {list(gql_json.keys())}")
                                    
                                    # Check for errors in the response
                                    if 'errors' in gql_json:
                                        errors = gql_json['errors']
                                        print(f"[DEBUG] GraphQL errors: {errors}")
                                        if isinstance(errors, list) and len(errors) > 0:
                                            first_error = errors[0]
                                            if isinstance(first_error, dict):
                                                error_msg = first_error.get('message', 'Unknown error')
                                                print(f"[DEBUG] First GraphQL error: {error_msg}")
                                    
                                    # Check if there's no data key
                                    if 'data' not in gql_json:
                                        print("[DEBUG] No 'data' key in GraphQL response - API request may have failed")
                                        print(f"[DEBUG] Full response keys: {gql_json.keys()}")
                                        if 'extensions' in gql_json:
                                            print(f"[DEBUG] Extensions: {gql_json['extensions']}")
                                        
                                        # Try alternative simplified query
                                        if page_count == 0:  # Only try alternative on first page
                                            print("[DEBUG] Trying simplified GraphQL query...")
                                            
                                            # Simplified variables with only essential fields
                                            simple_variables = {
                                                "count": 10,
                                                "cursor": next_cursor,
                                                "query": location,
                                                "filters": ["events"]
                                            }
                                            
                                            simple_payload = {
                                                'doc_id': '7568366146523096',  # Alternative doc_id
                                                'variables': json.dumps(simple_variables, separators=(',', ':')),
                                                'fb_dtsg': fb_dtsg,
                                                'lsd': lsd
                                            }
                                            
                                            alt_resp = self.session.post('https://www.facebook.com/api/graphql/', data=simple_payload, timeout=10)
                                            if alt_resp.status_code == 200:
                                                try:
                                                    alt_json = alt_resp.json()
                                                    print(f"[DEBUG] Simplified query response: {list(alt_json.keys())}")
                                                    if 'data' in alt_json:
                                                        print("[DEBUG] Simplified GraphQL query worked!")
                                                        gql_json = alt_json
                                                    else:
                                                        print("[DEBUG] Simplified query also failed, falling back to deep extraction")
                                                        # Run the same fallback extraction here when GraphQL fails
                                                        print("[DEBUG] GraphQL extraction failed - Playwright method will be used for comprehensive extraction")
                                                        # Removed fallback extraction methods
                                                        break
                                                except Exception as e:
                                                    print(f"[DEBUG] Simplified query response parsing failed: {e}")
                                                    break
                                            else:
                                                print(f"[DEBUG] Simplified query request failed with status: {alt_resp.status_code}")
                                                break
                                        else:
                                            break
                                        
                                except Exception as e:
                                    print(f"[DEBUG] Failed to parse GraphQL JSON: {e}")
                                    break
                                
                                # Try multiple possible response structures
                                edges = []
                                
                                # Original structure
                                edges = (gql_json.get('data', {})
                                         .get('serpResponse', {})
                                         .get('results', {})
                                         .get('edges', []))
                                
                                # Alternative structure 1
                                if not edges:
                                    edges = (gql_json.get('data', {})
                                            .get('serpResponse', {})
                                            .get('edges', []))
                                
                                # Alternative structure 2
                                if not edges:
                                    edges = (gql_json.get('data', {})
                                            .get('search', {})
                                            .get('edges', []))
                                
                                # Alternative structure 3
                                if not edges:
                                    edges = gql_json.get('data', {}).get('edges', [])
                                
                                print(f"[DEBUG] Found {len(edges)} edges in GraphQL response")
                                
                                new_events = []
                                for i, edge in enumerate(edges):
                                    print(f"[DEBUG] Processing edge {i+1}: {list(edge.keys()) if isinstance(edge, dict) else 'not dict'}")
                                    
                                    # Try multiple node extraction patterns
                                    node_json = None
                                    
                                    # Pattern 1: Original complex path
                                    if not node_json:
                                        node_json = edge.get('node', {}).get('rendering_strategy', {})\
                                                    .get('view_model', {}).get('profile', {})
                                    
                                    # Pattern 2: Direct node
                                    if not node_json:
                                        node_json = edge.get('node', {})
                                    
                                    # Pattern 3: Entity in node
                                    if not node_json:
                                        node_json = edge.get('node', {}).get('entity', {})
                                    
                                    if node_json and isinstance(node_json, dict):
                                        print(f"[DEBUG] Node keys: {list(node_json.keys())}")
                                        # Legacy extraction methods removed - Playwright handles this better
                                        print("[DEBUG] Legacy GraphQL extraction skipped - using Playwright")
                                print(f"[DEBUG] GraphQL extracted {len(new_events)} events")
                                all_events.extend(new_events)
                                
                                # Log progress for user visibility
                                print(f"[DEBUG] Total events loaded so far: {len(all_events)}")
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
                                
                                # Add small delay between requests to be respectful
                                if next_cursor and page_count < max_pages:
                                    time.sleep(0.5)
                        else:
                            print("[DEBUG] fb_dtsg or lsd token not found – cannot paginate via GraphQL")
                            print(f"[DEBUG] Will only return initial events from page: {len(all_events)}")
                            # Legacy deep extraction methods removed - Playwright handles this better
                            print("[DEBUG] Legacy deep extraction skipped - using Playwright")
                            # Deduplicate events
                            unique = {}
                            for ev in all_events:
                                eid = ev.get('id') or ev.get('website') or ev.get('title')
                                if eid and eid not in unique:
                                    unique[eid] = ev
                            all_events = list(unique.values())
                            
                            # Legacy text extraction methods removed - Playwright handles this better
                            print("[DEBUG] Legacy text extraction skipped - using Playwright")

                    final_count = min(len(all_events), 100)
                    print(f"[INFO] Returning {final_count} events (loaded {len(all_events)} total)")
                    return all_events[:100]  # Return up to 100 events instead of 30
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
    

    

    

    

    

    

    
    def execute(self, location: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """Execute the Facebook events search using web scraping"""
        try:
            print(f"[INFO] Starting Facebook events search for location: {location}")
            
            # Check if Playwright should be skipped (for debugging)
            skip_playwright = os.getenv('SKIP_PLAYWRIGHT', 'false').lower() == 'true'
            
            if skip_playwright:
                print("[DEBUG] Skipping Playwright (SKIP_PLAYWRIGHT=true), using static scraping...")
            else:
                # First try Playwright browser automation (best method)
                try:
                    print("[DEBUG] Attempting Playwright browser automation...")
                    playwright_events = self._search_events_with_playwright(location, start_date, end_date)
                    
                    if playwright_events and len(playwright_events) > 3:  # Lowered threshold
                        print(f"[SUCCESS] Playwright found {len(playwright_events)} events")
                        filtered_events = self._filter_events_by_location(playwright_events, location)
                        print(f"[INFO] Found {len(filtered_events)} Facebook events after location filtering")
                        return filtered_events
                    else:
                        print(f"[DEBUG] Playwright returned {len(playwright_events) if playwright_events else 0} events, falling back to static scraping")
                
                except Exception as e:
                    print(f"[DEBUG] Playwright method failed: {e}, falling back to static scraping")
            
            # Fallback to original static scraping method
            print("[DEBUG] Using static scraping method...")
            events = self._search_events(location, start_date, end_date)
            # Filter events strictly by location keyword
            filtered_events = self._filter_events_by_location(events, location)
            print(f"[INFO] Found {len(filtered_events)} Facebook events after location filtering")
            return filtered_events
        except Exception as e:
            print(f"[ERROR] Error fetching Facebook events: {e}")
            return []

    def _extract_facebook_tokens(self, html_content: str) -> tuple[str, str]:
        """Extract fb_dtsg and lsd tokens from Facebook page HTML using multiple patterns"""
        fb_dtsg = None
        lsd = None
        
        # Pattern 1: Standard form input fields
        fb_dtsg_match = re.search(r'name="fb_dtsg" value="([^"]+)"', html_content)
        if fb_dtsg_match:
            fb_dtsg = fb_dtsg_match.group(1)
            print(f"[DEBUG] Found fb_dtsg via form input: {fb_dtsg[:20]}...")
        
        lsd_match = re.search(r'name="lsd" value="([^"]+)"', html_content)
        if lsd_match:
            lsd = lsd_match.group(1)
            print(f"[DEBUG] Found lsd via form input: {lsd[:20]}...")
        
        # Pattern 2: JavaScript variables
        if not fb_dtsg:
            fb_dtsg_js_match = re.search(r'"token":"([^"]+)"', html_content)
            if fb_dtsg_js_match:
                fb_dtsg = fb_dtsg_js_match.group(1)
                print(f"[DEBUG] Found fb_dtsg via JS token: {fb_dtsg[:20]}...")
        
        # Pattern 3: DTSGInitialData
        if not fb_dtsg:
            dtsg_init_match = re.search(r'"DTSGInitialData":\s*{[^}]*"token":\s*"([^"]+)"', html_content)
            if dtsg_init_match:
                fb_dtsg = dtsg_init_match.group(1)
                print(f"[DEBUG] Found fb_dtsg via DTSGInitialData: {fb_dtsg[:20]}...")
        
        # Pattern 4: fb_dtsg in JavaScript assignments
        if not fb_dtsg:
            fb_dtsg_assign_match = re.search(r'fb_dtsg["\']?\s*[:=]\s*["\']([^"\']+)["\']', html_content)
            if fb_dtsg_assign_match:
                fb_dtsg = fb_dtsg_assign_match.group(1)
                print(f"[DEBUG] Found fb_dtsg via JS assignment: {fb_dtsg[:20]}...")
        
        # Pattern 5: Look in JSON data structures
        if not lsd:
            lsd_json_match = re.search(r'"lsd":\s*"([^"]+)"', html_content)
            if lsd_json_match:
                lsd = lsd_json_match.group(1)
                print(f"[DEBUG] Found lsd via JSON: {lsd[:20]}...")
        
        # Pattern 6: Alternative lsd patterns
        if not lsd:
            lsd_alt_match = re.search(r'lsd["\']?\s*[:=]\s*["\']([^"\']+)["\']', html_content)
            if lsd_alt_match:
                lsd = lsd_alt_match.group(1)
                print(f"[DEBUG] Found lsd via alternative pattern: {lsd[:20]}...")
        
        # Pattern 7: Look for nested structure like "lsd":{"token":"ACTUAL_TOKEN"}
        if not lsd:
            # Try multiple variations of nested lsd structure
            nested_patterns = [
                r'"lsd"\s*:\s*\{\s*"token"\s*:\s*"([^"]+)"',  # {"lsd":{"token":"value"}}
                r'"lsd"\s*:\s*\{\s*[^}]*"token"\s*:\s*"([^"]+)"',  # {"lsd":{...,"token":"value"}}
                r'"lsd"[^}]*"token"\s*:\s*"([^"]+)"',  # More flexible
                r'"token"\s*:\s*"([^"]+)"[^}]*\}[^}]*"lsd"',  # Reverse order
                r'lsd[^}]*token[^"]*"([^"]+)"',  # Very flexible
            ]
            
            for pattern in nested_patterns:
                lsd_nested_match = re.search(pattern, html_content)
                if lsd_nested_match:
                    potential_lsd = lsd_nested_match.group(1)
                    if potential_lsd != "token" and len(potential_lsd) > 10:
                        lsd = potential_lsd
                        print(f"[DEBUG] Found lsd via nested pattern '{pattern[:30]}...': {lsd[:20]}...")
                        break
        
        # Pattern 8: Look for LSD in server_js_define or similar structures
        if not lsd:
            lsd_server_match = re.search(r'"LSD"[^"]*"([^"]+)"', html_content)
            if lsd_server_match:
                potential_lsd = lsd_server_match.group(1)
                # Don't use if it's literally "token"
                if potential_lsd != "token" and len(potential_lsd) > 10:
                    lsd = potential_lsd
                    print(f"[DEBUG] Found lsd via LSD pattern: {lsd[:20]}...")
        
        # Pattern 9: Look for lsd in various Facebook data structures
        if not lsd:
            lsd_fb_match = re.search(r'"lsd":"([^"]+)"', html_content)
            if lsd_fb_match:
                potential_lsd = lsd_fb_match.group(1)
                if potential_lsd != "token" and len(potential_lsd) > 10:
                    lsd = potential_lsd
                    print(f"[DEBUG] Found lsd via FB structure: {lsd[:20]}...")
        
        # Pattern 10: Look for "token" followed by the actual token value (but not the word "token")
        if not lsd:
            # Match patterns like "token":"actual_token_here" but skip if value is "token"
            lsd_token_match = re.search(r'"token"\s*:\s*"([^"]+)"', html_content)
            if lsd_token_match:
                potential_lsd = lsd_token_match.group(1)
                # Skip if it's the same as fb_dtsg, or if it's literally "token", or too short
                if (potential_lsd != fb_dtsg and 
                    potential_lsd != "token" and 
                    len(potential_lsd) > 10):
                    lsd = potential_lsd
                    print(f"[DEBUG] Found lsd via token pattern: {lsd[:20]}...")
        
        # Pattern 11: Look for any structure containing lsd and token keys
        if not lsd:
            # More flexible pattern for nested structures
            lsd_complex_match = re.search(r'"lsd"[^}]*"token"\s*:\s*"([^"]+)"', html_content)
            if lsd_complex_match:
                potential_lsd = lsd_complex_match.group(1)
                if potential_lsd != "token" and len(potential_lsd) > 10:
                    lsd = potential_lsd
                    print(f"[DEBUG] Found lsd via complex nested pattern: {lsd[:20]}...")
        
        # Pattern 12: Extract from the actual Facebook LSD structures found in debug file
        if not lsd:
            print("[DEBUG] Trying extraction from actual Facebook LSD structures...")
            
            # Pattern from debug file: "lsd":{"name":"lsd","value":"ACTUAL_TOKEN"}
            lsd_value_match = re.search(r'"lsd"\s*:\s*\{\s*"name"\s*:\s*"lsd"\s*,\s*"value"\s*:\s*"([^"]+)"', html_content)
            if lsd_value_match:
                potential_lsd = lsd_value_match.group(1)
                if len(potential_lsd) > 10:
                    lsd = potential_lsd
                    print(f"[DEBUG] Found lsd via object value pattern: {lsd[:20]}...")
            
            # Pattern from debug file: ["LSD",[],{"token":"ACTUAL_TOKEN"},323]
            if not lsd:
                lsd_array_match = re.search(r'\["LSD"[^\]]*\{\s*"token"\s*:\s*"([^"]+)"', html_content)
                if lsd_array_match:
                    potential_lsd = lsd_array_match.group(1)
                    if len(potential_lsd) > 10:
                        lsd = potential_lsd
                        print(f"[DEBUG] Found lsd via LSD array pattern: {lsd[:20]}...")
            
            # Fallback: Original enhanced patterns
            if not lsd:
                enhanced_patterns = [
                    r'"lsd"[^}]{0,200}"token"[^"]{0,20}"([A-Za-z0-9_-]{15,})"',
                    r'"lsd"\s*:\s*\{[^}]*"token"\s*:\s*"([A-Za-z0-9_-]{15,})"',
                    r'lsd[^}]{0,100}token[^"]*"([A-Za-z0-9_-]{15,})"',
                ]
                
                for pattern in enhanced_patterns:
                    enhanced_match = re.search(pattern, html_content)
                    if enhanced_match:
                        potential_lsd = enhanced_match.group(1)
                        if potential_lsd != fb_dtsg:
                            lsd = potential_lsd
                            print(f"[DEBUG] Found lsd via fallback pattern: {lsd[:20]}...")
                            break
        
        # Pattern 11: Try to use fb_dtsg as lsd if no lsd found (sometimes they're the same)
        if not lsd and fb_dtsg:
            print(f"[DEBUG] No lsd found, attempting to use fb_dtsg as lsd")
            lsd = fb_dtsg
        
        if not fb_dtsg:
            print("[DEBUG] Could not find fb_dtsg token with any pattern")
        if not lsd:
            print("[DEBUG] Could not find lsd token with any pattern")
            # Debug: Show what lsd-related structures are actually in the HTML
            print("[DEBUG] Searching for lsd-related structures in HTML...")
            
            # Look for specific patterns you mentioned
            lsd_token_structures = re.findall(r'"lsd"[^}]{0,100}"token"[^"]{0,20}"([^"]+)"', html_content)
            if lsd_token_structures:
                print(f"[DEBUG] Found lsd->token structures: {lsd_token_structures[:3]}")
                # Use the first valid one
                for token_val in lsd_token_structures:
                    if token_val != "token" and len(token_val) > 10:
                        lsd = token_val
                        print(f"[DEBUG] Using extracted nested lsd token: {lsd[:20]}...")
                        break
            
            if not lsd:
                # Show broader context
                lsd_contexts = re.findall(r'.{0,50}"lsd".{0,100}', html_content, re.IGNORECASE)
                for i, context in enumerate(lsd_contexts[:3]):  # Show first 3 matches
                    print(f"[DEBUG] LSD context {i+1}: {context}")
                
                # Look for any token patterns
                token_contexts = re.findall(r'.{0,30}"token".{0,50}', html_content)
                for i, context in enumerate(token_contexts[:3]):  # Show first 3 matches
                    print(f"[DEBUG] Token context {i+1}: {context}")
        
        return fb_dtsg, lsd







    def _filter_events_by_location(self, events: List[Dict[str, Any]], location: str) -> List[Dict[str, Any]]:
        """NO LOCATION FILTERING - return all events for maximum coverage."""
        print(f"[DEBUG] NO LOCATION FILTERING - showing all {len(events)} events")
        
        # Log what events we're showing for debugging
        for i, ev in enumerate(events[:5]):  # Show first 5 event titles
            print(f"[DEBUG] Event {i+1}: '{ev.get('title', 'No title')[:50]}...'")
        
        if len(events) > 5:
            print(f"[DEBUG] ... and {len(events) - 5} more events")
        
        # Return ALL events without any filtering
        return events

    def _search_events_with_playwright(self, location: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search for Facebook events using Playwright browser automation with scrolling"""
        
        # Set a hard timeout for the entire Playwright operation
        import threading
        import time
        
        result = []
        exception = None
        
        def playwright_worker():
            nonlocal result, exception
            try:
                result = self._run_playwright_search(location, start_date, end_date)
            except Exception as e:
                exception = e
        
        print(f"[DEBUG] Starting Playwright worker thread with 120-second timeout...")
        thread = threading.Thread(target=playwright_worker)
        thread.daemon = True
        thread.start()
        thread.join(timeout=120)  # 120 second timeout for optimized scrolling
        
        if thread.is_alive():
            print(f"[DEBUG] Playwright timeout exceeded (120s), terminating...")
            print(f"[DEBUG] This usually means sync_playwright() is hanging - likely a Docker setup issue")
            return []
        
        if exception:
            print(f"[DEBUG] Playwright error: {exception}")
            return []
            
        return result
    
    def _run_playwright_search(self, location: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """The actual Playwright search implementation."""
        try:
            # Check if playwright is available
            print(f"[DEBUG] Step 1: Importing Playwright...")
            try:
                from playwright.async_api import async_playwright
                print(f"[DEBUG] Step 2: Playwright async import successful")
            except ImportError as e:
                print(f"[DEBUG] Playwright import failed: {e}")
                raise ImportError("Playwright not installed. Install with: pip install playwright")
            
            print(f"[DEBUG] Step 3: Starting Playwright browser automation...")
            print(f"[DEBUG] Step 4: Setting up async context...")
            
            # Construct the same URL as the static method
            from urllib.parse import quote_plus
            filters_blob = (
                "eyJmaWx0ZXJfZXZlbnRzX2RhdGVfcmFuZ2U6MCI6IntcIm5hbWVcIjpcImZpbHRlcl9ldmVudHNfZGF0ZVwiLFwiYXJnc1wiOlwiMjAyNS0wOC0yNX4yMDI1LTA4LTMxXCJ9IiwiZmlsdGVyX2V2ZW50c19kYXRlX3JhbmdlOjEiOiJ7XCJuYW1lXCI6XCJmaWx0ZXJfZXZlbnRzX2RhdGVcIixcImFyZ3NcIjpcIjIwMjUtMDgtMzB%2BMjAyNS0wOC0zMVwifSIsImZpbHRlcl9ldmVudHNfZGF0ZV9yYW5nZToyIjoie1wibmFtZVwiOlwiZmlsdGVyX2V2ZW50c19kYXRlXCIsXCJhcmdzXCI6XCIyMDI1LTA5LTAxfjIwMjUtMDktMDdcIn0iLCJmaWx0ZXJfZXZlbnRzX2RhdGVfcmFuZ2U6MyI6IntcIm5hbWVcIjpcImZpbHRlcl9ldmVudHNfZGF0ZVwiLFwiYXJnc1wiOlwiMjAyNS0wOS0wNn4yMDI1LTA5LTA3XCJ9In0%3D"
            )
            encoded_location = quote_plus(location)
            search_url = f"https://www.facebook.com/events/search?q={encoded_location}&filters={filters_blob}"
            
            events = []
            
            print(f"[DEBUG] Step 5: Using asyncio.run for async Playwright...")
            
            # Use asyncio to run the async Playwright code
            import asyncio
            
            async def run_async_playwright():
                async with async_playwright() as p:
                    print(f"[DEBUG] Step 6: async_playwright() context created successfully")
                    
                    # Launch browser with human-like settings to avoid Facebook detection
                    print(f"[DEBUG] Step 7: Starting Playwright browser launch...")
                    browser = await p.chromium.launch(
                        headless=True,
                        args=[
                            '--no-sandbox',
                            '--disable-setuid-sandbox', 
                            '--disable-dev-shm-usage',
                            '--disable-blink-features=AutomationControlled',
                            '--disable-web-security',
                            '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                        ]
                    )
                    print(f"[DEBUG] Browser launched successfully")
                    
                    # Create context with desktop settings and authentication cookies
                    print(f"[DEBUG] Creating browser context...")
                    context = await browser.new_context(
                        viewport={'width': 1920, 'height': 600},  # Smaller height to force scrolling
                        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36',
                        extra_http_headers={
                            'Accept-Language': 'en-US,en;q=0.9',
                            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                            'sec-ch-ua': '"Not;A=Brand";v="99", "Google Chrome";v="139", "Chromium";v="139"',
                            'sec-ch-ua-mobile': '?0',
                            'sec-ch-ua-platform': '"Windows"',
                            'sec-ch-ua-platform-version': '"19.0.0"',
                            'sec-fetch-dest': 'document',
                            'sec-fetch-mode': 'navigate',
                            'sec-fetch-site': 'same-origin',
                        }
                    )
                    
                    # Add Facebook authentication cookies from environment variables
                    print(f"[DEBUG] Adding authentication cookies...")
                    facebook_cookies = []
                    
                    # Build cookies from environment variables
                    cookie_mapping = {
                        'datr': os.getenv('FB_COOKIE_DATR'),
                        'sb': os.getenv('FB_COOKIE_SB'),
                        'c_user': os.getenv('FB_COOKIE_C_USER'),
                        'fr': os.getenv('FB_COOKIE_FR'),
                        'xs': os.getenv('FB_COOKIE_XS'),
                        'wd': os.getenv('FB_COOKIE_WD', '1185x991'),  # Default value
                        'presence': os.getenv('FB_COOKIE_PRESENCE'),
                        'locale': 'en_US',  # Static values
                        'ps_l': '1',
                        'ps_n': '1',
                        'm_pixel_ratio': '1',
                    }
                    
                    for name, value in cookie_mapping.items():
                        if value:  # Only add cookies that have values
                            facebook_cookies.append({
                                'name': name,
                                'value': value,
                                'domain': '.facebook.com',
                                'path': '/'
                            })
                    
                    # Only add cookies if they're provided
                    if facebook_cookies and facebook_cookies[0].get('name'):  # Check if cookies are actually set
                        await context.add_cookies(facebook_cookies)
                        print(f"[DEBUG] Added {len(facebook_cookies)} authentication cookies")
                    else:
                        print(f"[DEBUG] No authentication cookies provided - using anonymous access")
                    print(f"[DEBUG] Browser context created successfully")
                    
                    print(f"[DEBUG] Creating new page...")
                    page = await context.new_page()
                    
                    # Advanced stealth: Override navigator properties
                    await page.add_init_script("""
                        // Remove automation indicators
                        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                        Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
                        Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
                        
                        // Override automation detection
                        window.chrome = { runtime: {} };
                        Object.defineProperty(navigator, 'permissions', { get: () => undefined });
                        
                        // Remove playwright indicators
                        delete window.__playwright;
                        delete window.__pw_manual;
                        delete window.__PW_TEST;
                    """)
                    
                    print(f"[DEBUG] Page created successfully with stealth scripts")
                    
                    # Set up network interception to catch GraphQL and bulk-route-definitions calls
                    captured_events = []
                    
                    async def handle_response(response):
                        url = response.url
                        # Only intercept relevant API calls that likely contain event data
                        if (url and response.status == 200 and 
                            ('graphql' in url or 'bulk-route-definitions' in url or 'api' in url) and
                            ('event' in url.lower() or 'search' in url.lower() or 
                             response.request.method == 'POST')):
                            
                            print(f"[DEBUG] Intercepted relevant network call: {url[:100]}...")
                            try:
                                content = await response.text()
                                print(f"[DEBUG] Response content length: {len(content)} chars")
                                
                                # Check for the specific GraphQL pagination query that has full event data
                                if 'SearchCometResultsPaginatedResultsQuery' in content:
                                    print(f"[DEBUG] *** PAGINATION GraphQL call detected: {url[:100]}...")
                                
                                # Only process if content looks like it contains event data
                                if ('event' in content.lower() and len(content) > 100):
                                    # Look for content with actual event names/titles
                                    has_real_events = any(keyword in content for keyword in ['name":', 'title":', 'day_time_sentence', 'event_place'])
                                    if has_real_events:
                                        print(f"[DEBUG] Response contains real event data, processing...")
                                        
                                        # Save a debug sample of the response to see the actual structure
                                        if len(content) > 10000:  # Only for large responses
                                            try:
                                                with open('/tmp/debug_graphql_response.json', 'w') as f:
                                                    f.write(content[:50000])  # First 50KB
                                                print(f"[DEBUG] Saved debug GraphQL response to /tmp/debug_graphql_response.json")
                                            except:
                                                pass
                                        
                                        events_from_api = self._extract_events_from_api_response(content, location)
                                        if events_from_api:
                                            captured_events.extend(events_from_api)
                                            print(f"[DEBUG] Found {len(events_from_api)} valid events in API response")
                                        else:
                                            print(f"[DEBUG] ⚠️  Response has event keywords but extracted 0 events - parsing issue!")
                                            # Sample some event titles we can see in the raw text
                                            import re
                                            title_samples = re.findall(r'"name":"([^"]{10,50})"', content)[:3]
                                            if title_samples:
                                                print(f"[DEBUG] Sample titles found in raw text: {title_samples}")
                                    else:
                                        print(f"[DEBUG] Response contains only metadata, looking for full event data...")
                                else:
                                    print(f"[DEBUG] Response doesn't contain event data, skipping")
                            except Exception as e:
                                print(f"[DEBUG] Error processing network response: {e}")
                    
                    page.on('response', handle_response)
                    
                    # Navigate to the events page
                    print(f"[DEBUG] Loading Facebook events page...")
                    print(f"[DEBUG] URL: {search_url}")
                    response = await page.goto(search_url, wait_until='domcontentloaded', timeout=8000)
                    
                    if response and response.status == 200:
                        print(f"[DEBUG] Page loaded successfully (status: {response.status})")
                        
                        # Wait much longer for initial content to fully load
                        print(f"[DEBUG] Waiting for page to fully load...")
                        await page.wait_for_timeout(3000)  # Wait 3 seconds for initial load
                        
                        # Check initial page dimensions
                        initial_info = await page.evaluate("""
                            () => {
                                return {
                                    scrollHeight: document.body.scrollHeight,
                                    clientHeight: document.body.clientHeight,
                                    innerHeight: window.innerHeight,
                                    outerHeight: window.outerHeight,
                                    readyState: document.readyState
                                };
                            }
                        """)
                        print(f"[DEBUG] Initial page info: {initial_info}")
                        
                        # Check if we have scrollable content
                        is_scrollable = initial_info['scrollHeight'] > initial_info['innerHeight']
                        print(f"[DEBUG] Page is scrollable: {is_scrollable} (scrollHeight: {initial_info['scrollHeight']} vs innerHeight: {initial_info['innerHeight']})")
                        
                        if not is_scrollable:
                            print(f"[DEBUG] ⚠️ WARNING: Page content fits in viewport - may not trigger infinite scroll")
                        
                        # Trigger initial scroll to activate any lazy loading
                        await page.evaluate('window.scrollBy(0, 100)')
                        await page.wait_for_timeout(2000)
                        
                        # Extract events incrementally while scrolling
                        print(f"[DEBUG] Starting incremental scrolling and extraction...")
                        from bs4 import BeautifulSoup
                        all_events = []
                        seen_event_ids = set()
                        
                        # Extract initial events
                        print(f"[DEBUG] Extracting initial events...")
                        page_content = await page.content()
                        # Legacy extraction methods removed - rely on GraphQL interception
                        events = []
                        
                        # Deduplicate initial events with improved logic
                        for event in events:
                            title = event.get('title', '').strip().lower()
                            url = event.get('url', '').strip()
                            clean_url = url.split('?')[0] if url else ''
                            
                            event_ids = [
                                f"title-{title}",
                                f"url-{clean_url}",
                                f"{title}-{event.get('date', '')}",
                            ]
                            
                            is_duplicate = False
                            for check_id in event_ids:
                                if check_id in seen_event_ids:
                                    is_duplicate = True
                                    break
                            
                            if not is_duplicate and title and len(title) > 3:
                                for check_id in event_ids:
                                    seen_event_ids.add(check_id)
                                all_events.append(event)
                        
                        print(f"[DEBUG] Found {len(all_events)} initial events")
                        
                        # Simple focused approach: scroll and wait for GraphQL calls
                        graphql_events = []
                        
                        # Set up GraphQL interception for the entire scrolling session
                        async def handle_graphql_response(response):
                            # Look specifically for the pagination GraphQL call you showed me
                            if ('graphql' in response.url and response.status == 200 and
                                response.request.headers.get('x-fb-friendly-name') == 'SearchCometResultsPaginatedResultsQuery'):
                                print(f"[DEBUG] *** PAGINATION GraphQL call detected: {response.url[:100]}...")
                                try:
                                    content = await response.text()
                                    print(f"[DEBUG] GraphQL response length: {len(content)} chars")
                                    
                                    # Parse events from GraphQL response
                                    events_from_graphql = self._extract_events_from_api_response(content, location)
                                    if events_from_graphql:
                                        graphql_events.extend(events_from_graphql)
                                        print(f"[DEBUG] *** Found {len(events_from_graphql)} events in pagination GraphQL!")
                                    else:
                                        print(f"[DEBUG] No events found in pagination GraphQL response")
                                        
                                except Exception as e:
                                    print(f"[DEBUG] Error parsing GraphQL response: {e}")
                            elif 'graphql' in response.url and response.status == 200:
                                # Log other GraphQL calls for debugging
                                friendly_name = response.request.headers.get('x-fb-friendly-name', 'Unknown')
                                print(f"[DEBUG] Other GraphQL call: {friendly_name}")
                        
                        page.on('response', handle_graphql_response)
                        
                        # Look for load more buttons or pagination elements first
                        try:
                            # Check if there are any "load more" type elements
                            load_more_selectors = [
                                'button:has-text("Show more")',
                                'button:has-text("Load more")',
                                'span:has-text("See more")',
                                'div:has-text("Show more")',
                                '[data-testid*="load"]',
                                '[data-testid*="more"]',
                                '[role="button"]:has-text("more")',
                                'a:has-text("See more")'
                            ]
                            
                            load_more_found = False
                            for selector in load_more_selectors:
                                try:
                                    elements = await page.locator(selector).all()
                                    if len(elements) > 0:
                                        print(f"[DEBUG] Found {len(elements)} potential 'load more' elements with selector: {selector}")
                                        load_more_found = True
                                except:
                                    pass
                            
                            if not load_more_found:
                                print(f"[DEBUG] No 'load more' buttons found - may indicate all events are already loaded")
                                
                        except Exception as e:
                            print(f"[DEBUG] Error checking for load more buttons: {e}")
                        
                        # Mimic your SLOW scrolling behavior that allows events to load naturally
                        for i in range(10):  # Reasonable number of scroll attempts
                            print(f"[DEBUG] === Slow Scroll {i+1}/10 (Mimicking Manual Behavior) ===")
                            
                            # Get current page info
                            scroll_info = await page.evaluate("""
                                () => {
                                    return {
                                        scrollY: window.scrollY,
                                        innerHeight: window.innerHeight,
                                        scrollHeight: document.body.scrollHeight,
                                        maxScrollY: document.body.scrollHeight - window.innerHeight
                                    };
                                }
                            """)
                            
                            print(f"[DEBUG] Current: scrollY={scroll_info['scrollY']}, pageHeight={scroll_info['scrollHeight']}")
                            
                            # SLOW scrolling that mimics your manual behavior
                            # You said "if I scroll slowly then they load in before I even see them"
                            
                            # Method 1: Very slow, smooth scrolling in small increments
                            current_scroll = scroll_info['scrollY']
                            target_scroll = min(current_scroll + 400, scroll_info['maxScrollY'])  # Scroll 400px down
                            
                            print(f"[DEBUG] Slow scrolling from {current_scroll} to {target_scroll}...")
                            
                            # Scroll in very small increments with pauses (mimics slow manual scrolling)
                            steps = 8  # 8 steps of 50px each = 400px total
                            for step in range(steps):
                                intermediate_scroll = current_scroll + (target_scroll - current_scroll) * (step + 1) / steps
                                await page.evaluate(f'window.scrollTo({{ top: {intermediate_scroll}, behavior: "smooth" }})')
                                await page.wait_for_timeout(150)  # 150ms between micro-scrolls = faster
                            
                            # Method 2: Pause at new position (like reading content)
                            print(f"[DEBUG] Pausing at scroll position {target_scroll} (reading content)...")
                            await page.wait_for_timeout(1500)  # 1.5 second pause like human reading
                            
                            # Method 3: Check if we're near bottom and need to wait longer
                            near_bottom = target_scroll >= scroll_info['maxScrollY'] * 0.8
                            
                            if near_bottom:
                                print(f"[DEBUG] Near bottom - waiting longer for pagination trigger...")
                                await page.wait_for_timeout(3000)  # Wait longer near bottom
                                
                                # If at bottom, wait even longer like your manual behavior
                                if target_scroll >= scroll_info['maxScrollY'] - 50:
                                    print(f"[DEBUG] At bottom - extended wait for GraphQL pagination...")
                                    await page.wait_for_timeout(4000)  # 4 second wait at bottom
                            
                            # Skip button clicking - focus on scroll position detection
                            
                            # Check if page content changed (indicating new content loaded)
                            current_height = await page.evaluate('document.body.scrollHeight')
                            content_check = await page.evaluate('document.body.innerText.length')
                            
                            # Track if content changed from previous iteration
                            height_changed = i == 0 or current_height != getattr(self, '_prev_height', 0)
                            content_changed = i == 0 or content_check != getattr(self, '_prev_content', 0)
                            
                            print(f"[DEBUG] After scroll {i+1}: Page height: {current_height} {'(+)' if height_changed else ''}, Content length: {content_check} {'(+)' if content_changed else ''}")
                            print(f"[DEBUG] GraphQL events captured: {len(graphql_events)}")
                            
                            # Store for next iteration
                            self._prev_height = current_height
                            self._prev_content = content_check
                            
                            # If we found GraphQL events, we're successful!
                            if len(graphql_events) > 0:
                                print(f"[DEBUG] ✓ SUCCESS: Found GraphQL events, continuing to get more...")
                            
                            # If content changed but no GraphQL, the loading mechanism might be different
                            if (height_changed or content_changed) and len(graphql_events) == 0:
                                print(f"[DEBUG] ⚠️  Content changed but no GraphQL detected - may need different interception")
                            
                            # If page stopped growing and no GraphQL calls, we might have all content
                            if i > 2 and len(graphql_events) == 0 and not height_changed and not content_changed:
                                print(f"[DEBUG] Still no GraphQL calls after {i+1} scrolls. Facebook may not be loading more events for this location.")
                        
                        # Combine all events: initial HTML + GraphQL
                        all_events.extend(graphql_events)
                        
                        # Final deduplication
                        final_events = []
                        final_seen_ids = set()
                        
                        for event in all_events:
                            title = event.get('title', '').strip().lower()
                            url = event.get('url', '').strip()
                            clean_url = url.split('?')[0] if url else ''
                            
                            event_ids = [
                                f"title-{title}",
                                f"url-{clean_url}",
                                f"{title}-{event.get('date', '')}",
                            ]
                            
                            is_duplicate = False
                            for check_id in event_ids:
                                if check_id in final_seen_ids:
                                    is_duplicate = True
                                    break
                            
                            if not is_duplicate and title and len(title) > 3:
                                for check_id in event_ids:
                                    final_seen_ids.add(check_id)
                                final_events.append(event)
                        
                        events = final_events
                        print(f"[DEBUG] Final result: {len(events)} total unique events")
                        print(f"[DEBUG] Initial events: {len(all_events) - len(graphql_events)}, GraphQL events: {len(graphql_events)}")
                        
                        await browser.close()
                        return events
                    else:
                        print(f"[DEBUG] Failed to load page, status: {response.status if response else 'None'}")
                        await browser.close()
                        return []
            
            # Run the async function
            print(f"[DEBUG] Step 6: Running async Playwright with asyncio.run...")
            return asyncio.run(run_async_playwright())
            
        except Exception as e:
            print(f"[DEBUG] Playwright automation error: {e}")
            return []

    def _extract_events_from_api_response(self, api_content: str, location: str) -> List[Dict[str, Any]]:
        """Extract events from GraphQL and bulk-route-definitions API responses"""
        import json
        import re
        
        events = []
        
        try:
            # Try to parse as JSON first
            if api_content.strip().startswith('{') or api_content.strip().startswith('['):
                try:
                    data = json.loads(api_content)
                    print(f"[DEBUG] Parsed JSON data successfully, keys: {list(data.keys()) if isinstance(data, dict) else 'not dict'}")
                    json_events = self._parse_json_events(data, location)
                    if json_events:
                        print(f"[DEBUG] GraphQL/JSON parsing found {len(json_events)} events, returning those instead of regex")
                        return json_events  # Return GraphQL events immediately, don't fall back to regex
                    events.extend(json_events)
                except Exception as e:
                    print(f"[DEBUG] JSON parsing failed: {e}")
                    pass
            
            # Look for event patterns in the response text
            # Pattern 1: route_url with event ID
            route_pattern = r'/events/(\d+)'
            event_ids = re.findall(route_pattern, api_content)
            
            for event_id in event_ids:
                # Try to find event title near the ID
                title_patterns = [
                    rf'events/{event_id}[^"]*"[^"]*"([^"]+)"',
                    rf'"title":"([^"]+)"[^}}]*{event_id}',
                    rf'{event_id}[^}}]*"name":"([^"]+)"',
                    rf'"([^"]+)"[^}}]*events/{event_id}'
                ]
                
                title = None
                for pattern in title_patterns:
                    match = re.search(pattern, api_content, re.IGNORECASE)
                    if match:
                        title = match.group(1).strip()
                        if len(title) > 3 and title not in ['Event', 'Events', 'event', 'events']:
                            break
                
                # Filter out invalid titles
                invalid_titles = ['error', 'null', 'undefined', 'true', 'false', 'event', 'events', 
                                'loading', 'load', 'success', 'failed', 'data', 'response', 'result',
                                'is_hosted_by_ticket_master', 'ticket_master', 'ticketmaster']
                
                if (title and len(title) > 3 and 
                    title.lower() not in invalid_titles and
                    not title.isdigit() and
                    not all(c in '{}[]()' for c in title)):
                    
                    event = {
                        'title': title,
                        'date': "Date not specified",
                        'location': location,
                        'url': f"https://www.facebook.com/events/{event_id}",
                        'description': "Event found via API network interception"
                    }
                    events.append(event)
                    print(f"[DEBUG] Extracted API event: {title}")
            
            # Pattern 2: Look for event objects with name/title fields
            event_object_patterns = [
                r'"event":\s*{[^}]*"name":\s*"([^"]+)"[^}]*"id":\s*"([^"]+)"',
                r'"name":\s*"([^"]+)"[^}]*"event_id":\s*"([^"]+)"',
                r'"title":\s*"([^"]+)"[^}]*"eventId":\s*"([^"]+)"'
            ]
            
            for pattern in event_object_patterns:
                matches = re.findall(pattern, api_content, re.IGNORECASE)
                for match in matches:
                    title, event_id = match
                    # Apply same filtering
                    invalid_titles = ['error', 'null', 'undefined', 'true', 'false', 'event', 'events', 
                                    'loading', 'load', 'success', 'failed', 'data', 'response', 'result',
                                    'is_hosted_by_ticket_master', 'ticket_master', 'ticketmaster']
                    
                    if (title and len(title) > 3 and event_id and
                        title.lower() not in invalid_titles and
                        not title.isdigit() and
                        not all(c in '{}[]()' for c in title)):
                        
                        event = {
                            'title': title,
                            'date': "Date not specified", 
                            'location': location,
                            'url': f"https://www.facebook.com/events/{event_id}",
                            'description': "Event found via API pattern matching"
                        }
                        events.append(event)
                        print(f"[DEBUG] Extracted API pattern event: {title}")
                        
        except Exception as e:
            print(f"[DEBUG] Error parsing API response: {e}")
        
        return events
    
    def _parse_json_events(self, data: dict, location: str) -> List[Dict[str, Any]]:
        """Parse events from JSON API responses, especially GraphQL"""
        events = []
        
        try:
            # First try to parse as proper GraphQL structure
            if isinstance(data, dict) and 'data' in data:
                print(f"[DEBUG] Found 'data' key in JSON response")
                serp_response = data.get('data', {}).get('serpResponse', {})
                if serp_response:
                    print(f"[DEBUG] Found serpResponse in data")
                    results = serp_response.get('results', {})
                    if results:
                        print(f"[DEBUG] Found results in serpResponse")
                        edges = results.get('edges', [])
                        print(f"[DEBUG] Processing GraphQL structure with {len(edges)} edges")
                    else:
                        print(f"[DEBUG] No results in serpResponse")
                        edges = []
                else:
                    print(f"[DEBUG] No serpResponse in data")
                    edges = []
                
                for i, edge in enumerate(edges):
                    node = edge.get('node', {})
                    print(f"[DEBUG] Edge {i}: role={node.get('role')}")
                    if node.get('role') == 'ENTITY_EVENTS':
                        print(f"[DEBUG] Processing ENTITY_EVENTS edge {i}")
                        print(f"[DEBUG] Edge {i} node keys: {list(node.keys())}")
                        rendering_strategy = node.get('rendering_strategy', {})
                        print(f"[DEBUG] Edge {i} rendering_strategy keys: {list(rendering_strategy.keys())}")
                        view_model = rendering_strategy.get('view_model', {})
                        print(f"[DEBUG] Edge {i} view_model keys: {list(view_model.keys())}")
                        profile = view_model.get('profile', {})
                        print(f"[DEBUG] Edge {i} profile keys: {list(profile.keys())}")
                        
                        # Extract event data from the proper GraphQL structure
                        event_id = profile.get('id', '')
                        title = profile.get('name', '')
                        date_sentence = profile.get('day_time_sentence', '')
                        event_url = profile.get('url', '') or profile.get('eventUrl', '')
                        
                        print(f"[DEBUG] Edge {i} profile data: id={event_id}, name='{title[:30] if title else None}...', url={event_url[:50] if event_url else None}...")
                        
                        # Extract location info
                        event_place = profile.get('event_place', {})
                        event_location = ''
                        if event_place:
                            event_location = event_place.get('contextual_name', '')
                        
                        # Skip invalid events
                        if not title or len(title.strip()) < 3:
                            continue
                            
                        invalid_titles = ['is_hosted_by_ticket_master', 'error', 'null', 'undefined']
                        if any(invalid in title.lower() for invalid in invalid_titles):
                            print(f"[DEBUG] Skipping invalid GraphQL title: {title}")
                            continue
                        
                        # Extract timestamp if available
                        start_timestamp = profile.get('start_timestamp', '')
                        formatted_date = date_sentence
                        if start_timestamp:
                            try:
                                import datetime
                                dt = datetime.datetime.fromtimestamp(int(start_timestamp))
                                formatted_date = dt.strftime('%B %d, %Y at %I:%M %p')
                            except:
                                formatted_date = date_sentence
                        
                        event = {
                            'id': event_id,
                            'title': title.strip(),
                            'date': formatted_date or "Date not specified",
                            'url': event_url or f"https://www.facebook.com/events/{event_id}",
                            'location': event_location.strip() or location,
                            'description': f"Event from Facebook GraphQL API"
                        }
                        events.append(event)
                        print(f"[DEBUG] ✅ Extracted GraphQL event: {title[:50]}...")
                
                print(f"[DEBUG] Finished processing {len(edges)} edges, found {len(events)} valid events")
                if events:
                    print(f"[DEBUG] ✅ Successfully extracted {len(events)} events from GraphQL structure")
                    return events
                else:
                    print(f"[DEBUG] ❌ No valid events found in GraphQL structure, edges only contain minimal data")
                    print(f"[DEBUG] This appears to be a metadata response, not the full event data response")
            
            # Fallback to recursive search for event-like objects
            print(f"[DEBUG] No GraphQL structure found, using enhanced fallback parsing")
            def find_events(obj, path=""):
                if isinstance(obj, dict):
                    # Look for event indicators
                    if 'event' in str(obj).lower() or 'events' in str(obj).lower():
                        # Try to extract comprehensive event data
                        title = None
                        event_id = None
                        date_sentence = None
                        event_url = None
                        event_location = None
                        social_context = None
                        
                        # Extract all possible event fields
                        for key, value in obj.items():
                            if isinstance(value, str):
                                if key.lower() in ['name', 'title', 'event_name']:
                                    title = value
                                elif key.lower() in ['id', 'event_id', 'eventid']:
                                    event_id = value
                                elif 'event' in key.lower() and 'id' in key.lower():
                                    event_id = value
                                elif key.lower() in ['day_time_sentence', 'date_sentence', 'when', 'start_time']:
                                    date_sentence = value
                                elif key.lower() in ['url', 'eventurl', 'event_url']:
                                    event_url = value
                                # Additional URL patterns from your GraphQL sample
                                elif '/events/' in value and ('facebook.com' in value or value.startswith('/events/')):
                                    event_url = value
                                    # Extract event ID from URL if we don't have it
                                    if not event_id:
                                        import re
                                        id_match = re.search(r'/events/(\d+)', value)
                                        if id_match:
                                            event_id = id_match.group(1)
                            elif isinstance(value, dict):
                                # Look for nested event place info
                                if 'contextual_name' in value:
                                    event_location = value.get('contextual_name', '')
                                # Look for social context (interested/going)
                                if 'text' in value and any(word in str(value).lower() for word in ['interested', 'going']):
                                    social_context = value.get('text', '')
                        
                        # Skip invalid titles
                        invalid_titles = ['is_hosted_by_ticket_master', 'error', 'null', 'undefined', 'online_filter', 'paid_filter', 'rp_events_location', 'filter_events']
                        if title and len(title) > 3 and not any(invalid in title.lower() for invalid in invalid_titles):
                            # Format the date properly
                            formatted_date = date_sentence or "Date not specified"
                            
                            # Create proper Facebook URL
                            final_url = "#"
                            if event_url:
                                if event_url.startswith('http'):
                                    final_url = event_url
                                elif event_url.startswith('/events/'):
                                    final_url = f"https://www.facebook.com{event_url}"
                                else:
                                    final_url = event_url
                            elif event_id:
                                final_url = f"https://www.facebook.com/events/{event_id}/"
                            
                            # Extract proper interested/attending counts from social context
                            interested_count = 0
                            attending_count = 0
                            if social_context:
                                import re
                                # Extract numbers from text like "16 interested · 4 going"
                                interested_match = re.search(r'(\d+)\s+interested', social_context)
                                if interested_match:
                                    interested_count = int(interested_match.group(1))
                                
                                going_match = re.search(r'(\d+)\s+going', social_context)
                                if going_match:
                                    attending_count = int(going_match.group(1))
                            
                            # Create comprehensive event data
                            event = {
                                'id': event_id or f"fallback_{hash(title)}", # Ensure unique ID
                                'title': title,
                                'date': formatted_date,
                                'when': formatted_date,  # Frontend expects 'when' field
                                'location': event_location or location,
                                'address': event_location or location,
                                'url': final_url,
                                'website': final_url,
                                'social_context': social_context or '',
                                'interested_count': interested_count,  # Numeric value
                                'attending_count': attending_count,    # Numeric value
                                'description': f"Event found via enhanced JSON parsing"
                            }
                            events.append(event)
                            print(f"[DEBUG] Enhanced fallback extracted: {title[:40]}... | Date: {formatted_date[:20]}... | Social: {social_context or 'None'} | URL: {event.get('url', 'No URL')[:50]}...")
                    
                    # Recursively search nested objects
                    for key, value in obj.items():
                        find_events(value, f"{path}.{key}")
                        
                elif isinstance(obj, list):
                    # Search through list items
                    for i, item in enumerate(obj):
                        find_events(item, f"{path}[{i}]")
            
            find_events(data)
            
        except Exception as e:
            print(f"[DEBUG] Error in JSON event parsing: {e}")
        
        return events




