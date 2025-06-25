import os
import requests
import re
from typing import Dict, Any, List
from bs4 import BeautifulSoup
from .base_tool import BaseTool
from models.place import Place

class ContactScraperTool(BaseTool):
    """
    Enhanced tool for scraping contact information from event websites and Google Places.
    Input: {"location": str, "query": str (optional), "use_mock": bool (optional), "search_radius": int (optional)}
    Output: {"success": bool, "places": list, "count": int, "error": str (if any)}
    """

    def __call__(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            self.validate_input(input_data)
            
            location = input_data["location"]
            query = input_data.get("query", "Summer Camp")
            use_mock = input_data.get("use_mock", False)
            search_radius = input_data.get("search_radius", 5000)
            
            if use_mock:
                places = self._mock_scrape_nearby(location)
            else:
                places = self._scrape_real_events(location, query, search_radius)
            
            return {
                "success": True,
                "places": [place.__dict__ for place in places],
                "count": len(places)
            }
            
        except Exception as e:
            return self.handle_error(e)

    def validate_input(self, input_data: Dict[str, Any]) -> None:
        """Validate required input parameters."""
        required_fields = ["location"]
        for field in required_fields:
            if field not in input_data:
                raise ValueError(f"Missing required field: {field}")
            if not input_data[field] or not isinstance(input_data[field], str):
                raise ValueError(f"Field {field} must be a non-empty string")

    def _mock_scrape_nearby(self, location: str) -> List[Place]:
        """Enhanced mock scraping for testing purposes."""
        mock_results = [
            {
                "name": "Camp Sunshine Summer Program",
                "description": "Weekly day camp for ages 6–12 focused on outdoor activities and nature exploration.",
                "address": "200 Camp Sunshine Rd, Snellville, GA",
                "website": "https://campsunshine.org",
                "contact_email": "hello@campsunshine.org",
                "phone_number": "770-555-0123"
            },
            {
                "name": "Snellville Sports & Rec Meetup",
                "description": "Weekly evening sports meetup for local families. Basketball, soccer, and more.",
                "address": "500 Rec Center Dr, Snellville, GA",
                "website": "https://snellvillerec.org",
                "contact_email": "info@snellvillerec.org",
                "phone_number": "770-555-0124"
            },
            {
                "name": "Creative Minds Art Camp",
                "description": "Kids art camp for ages 5–10 focused on creativity and crafts. Painting, drawing, and sculpture.",
                "address": "300 Art Blvd, Snellville, GA",
                "website": "https://creativemindsart.com",
                "contact_email": "camp@creativemindsart.com",
                "phone_number": "770-555-0125"
            },
            {
                "name": "Snellville Farmers Market",
                "description": "Weekly farmers market featuring local produce, crafts, and live music.",
                "address": "100 Main St, Snellville, GA",
                "website": "https://snellvillefarmersmarket.org",
                "contact_email": "market@snellvillefarmersmarket.org",
                "phone_number": "770-555-0126"
            },
            {
                "name": "Snellville Community Theater",
                "description": "Local community theater productions and acting classes for all ages.",
                "address": "400 Theater Way, Snellville, GA",
                "website": "https://snellvilletheater.org",
                "contact_email": "info@snellvilletheater.org",
                "phone_number": "770-555-0127"
            }
        ]
        return [Place(**entry) for entry in mock_results]

    def _scrape_real_events(self, location: str, query: str = "Summer Camp", search_radius: int = 5000) -> List[Place]:
        """Enhanced scraping using Google Places API with better error handling."""
        from utils.geocode import geocode_address
        from data.locations import LOCATION_ADDRESSES
        
        api_key = os.getenv("GOOGLE_PLACES_API_KEY")
        if not api_key:
            raise ValueError("Missing GOOGLE_PLACES_API_KEY")

        # Get address and geocode
        address = LOCATION_ADDRESSES.get(location)
        if not address:
            raise ValueError(f"No address found for location: {location}")
        
        coords = geocode_address(address)
        lat, lon = coords["lat"], coords["lon"]

        search_url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        details_url = "https://maps.googleapis.com/maps/api/place/details/json"

        # Enhanced search queries for better results
        search_queries = [
            f"{query} {location}",
            f"{query} events {location}",
            f"{query} activities {location}",
            f"local {query} {location}"
        ]

        all_results = []

        for search_query in search_queries:
            search_params = {
                "query": search_query,
                "location": f"{lat},{lon}",
                "radius": search_radius,
                "key": api_key,
                "type": "establishment"  # Focus on businesses/establishments
            }

            try:
                res = requests.get(search_url, params=search_params, timeout=10)
                res.raise_for_status()
                data = res.json()
                all_results.extend(data.get("results", []))
            except Exception as e:
                print(f"Error searching for '{search_query}': {e}")
                continue

        # Remove duplicates based on place_id
        unique_results = {}
        for result in all_results:
            place_id = result.get("place_id")
            if place_id and place_id not in unique_results:
                unique_results[place_id] = result

        results = []

        for result in list(unique_results.values())[:10]:  # Limit to 10 results
            place_id = result.get("place_id")
            details_params = {
                "place_id": place_id,
                "fields": "name,website,formatted_address,types,editorial_summary,formatted_phone_number,opening_hours,rating,user_ratings_total",
                "key": api_key
            }
            
            try:
                details_res = requests.get(details_url, params=details_params, timeout=10)
                details_res.raise_for_status()
                details = details_res.json().get("result", {})

                website = details.get("website")
                email = self._extract_email_from_website(website) if website else None
                phone_number = details.get("formatted_phone_number")
                editorial = details.get("editorial_summary", {})
                overview = editorial.get("overview")
                description = overview or details.get("types", ["No description"])[0].replace("_", " ").title()

                results.append(Place(
                    name=details.get("name", "Unnamed Event"),
                    description=description,
                    address=details.get("formatted_address", "Unknown address"),
                    website=website,
                    contact_email=email,
                    phone_number=phone_number
                ))
            except Exception as e:
                print(f"Error getting details for place {place_id}: {e}")
                continue

        return results

    def _extract_email_from_website(self, url: str) -> str | None:
        """Enhanced email extraction from websites."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, timeout=10, headers=headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Look for emails in various places
            emails = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", soup.text)
            
            # Filter out common false positives
            filtered_emails = []
            for email in emails:
                if not any(exclude in email.lower() for exclude in ['example.com', 'test.com', 'domain.com']):
                    filtered_emails.append(email)
            
            return filtered_emails[0] if filtered_emails else None
        except Exception as e:
            print(f"Error extracting email from {url}: {e}")
            return None

# Convenience function for backward compatibility
def scrape_events(location: str, query: str = "Summer Camp", use_mock: bool = False):
    """Legacy function - use ContactScraperTool() instead."""
    tool = ContactScraperTool()
    result = tool({
        "location": location,
        "query": query,
        "use_mock": use_mock
    })
    if result["success"]:
        return result["places"]
    else:
        raise ValueError(result["error"]) 