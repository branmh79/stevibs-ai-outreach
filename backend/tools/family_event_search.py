from typing import Dict, Any, List
from .base_tool import BaseTool
from .google_search import GoogleSearchTool
from .contact_scraper import ContactScraperTool

class FamilyEventSearchTool(BaseTool):
    """
    Tool for finding family-focused events using Google Custom Search Engine and scraping contact info.
    Input: {
        "location": str,
        "use_mock": bool (optional, default=False),
        "search_radius": int (optional, default=5000)
    }
    Output: {
        "success": bool,
        "events": list,
        "total_count": int,
        "source_counts": dict,
        "errors": list
    }
    """

    def __init__(self):
        self.google_tool = GoogleSearchTool()
        self.scraper_tool = ContactScraperTool()
        self.family_categories = [
            "summer camp",
            "after school program",
            "youth sports",
            "school spirit day",
            "family recreation center",
            "ymca",
            "boys and girls club",
            "community center",
            "parks and recreation",
            "youth activities",
            "teen programs",
            "family events",
            "school events",
            "community sports",
            "youth clubs"
        ]

    def __call__(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            self.validate_input(input_data)
            location = input_data["location"]
            use_mock = input_data.get("use_mock", False)
            all_events = []
            source_counts = {}
            errors = []
            for category in self.family_categories:
                try:
                    # 1. Use GoogleSearchTool to get URLs
                    search_input = {
                        "location": location,
                        "event_type": category,
                        "num_results": 5
                    }
                    google_result = self.google_tool(search_input)
                    if not google_result["success"]:
                        errors.append(f"Google search failed for {category}: {google_result.get('error', 'Unknown error')}")
                        source_counts[category] = 0
                        continue
                    urls = [item["website"] for item in google_result["events"] if item.get("website")]
                    if not urls:
                        source_counts[category] = 0
                        continue
                    # 2. Scrape each URL for contact info
                    scrape_result = self.scraper_tool({"urls": urls})
                    if not scrape_result["success"]:
                        errors.append(f"Scraping failed for {category}: {scrape_result.get('error', 'Unknown error')}")
                        source_counts[category] = 0
                        continue
                    events = []
                    for item in scrape_result["results"]:
                        event = {
                            "title": item.get("title"),
                            "description": item.get("description"),
                            "website": item.get("url"),
                            "contact_email": item.get("contact_email"),
                            "phone_number": item.get("phone_number"),
                            "source": "family_scraper",
                            "category": category
                        }
                        # Debug: Print what we're adding
                        print(f"Adding event: {event}")
                        events.append(event)
                    all_events.extend(events)
                    source_counts[category] = len(events)
                except Exception as e:
                    errors.append(f"{category}: {str(e)}")
                    source_counts[category] = 0
            # Deduplicate events by title+website
            seen = set()
            unique_events = []
            for event in all_events:
                key = f"{(event.get('title') or '').lower().strip()}|{(event.get('website') or '').lower().strip()}"
                if key not in seen:
                    seen.add(key)
                    unique_events.append(event)
            return {
                "success": True,
                "events": unique_events,
                "total_count": len(unique_events),
                "source_counts": source_counts,
                "errors": errors
            }
        except Exception as e:
            return self.handle_error(e)

    async def search_async(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Asynchronous version of the search pipeline for better performance."""
        import asyncio
        from functools import partial
        self.validate_input(input_data)
        location = input_data["location"]
        use_mock = input_data.get("use_mock", False)

        all_events: List[Dict[str, Any]] = []
        source_counts: Dict[str, int] = {}
        errors: List[str] = []

        # Semaphore to limit concurrent categories (avoid hitting rate limits)
        semaphore = asyncio.Semaphore(5)

        async def process_category(category: str):
            async with semaphore:
                try:
                    # Google search (run in thread pool)
                    search_input = {
                        "location": location,
                        "event_type": category,
                        "num_results": 5,
                    }
                    loop = asyncio.get_running_loop()
                    google_result = await loop.run_in_executor(None, partial(self.google_tool, search_input))
                    if not google_result["success"]:
                        errors.append(f"Google search failed for {category}: {google_result.get('error', 'Unknown error')}")
                        source_counts[category] = 0
                        return []
                    urls = [item["website"] for item in google_result["events"] if item.get("website")]
                    if not urls:
                        source_counts[category] = 0
                        return []
                    # Scrape URLs concurrently (async method)
                    scrape_result = await self.scraper_tool.scrape_contacts_from_urls_async(urls)
                    events = []
                    for item in scrape_result:
                        events.append(
                            {
                                "title": item.get("title"),
                                "description": item.get("description"),
                                "website": item.get("url"),
                                "contact_email": item.get("contact_email"),
                                "phone_number": item.get("phone_number"),
                                "source": "family_scraper",
                                "category": category,
                            }
                        )
                    source_counts[category] = len(events)
                    return events
                except Exception as e:
                    errors.append(f"{category}: {str(e)}")
                    source_counts[category] = 0
                    return []

        tasks = [process_category(c) for c in self.family_categories]
        for coro in asyncio.as_completed(tasks):
            events = await coro
            all_events.extend(events)

        # Deduplicate events
        seen = set()
        unique_events: List[Dict[str, Any]] = []
        for event in all_events:
            key = f"{(event.get('title') or '').lower().strip()}|{(event.get('website') or '').lower().strip()}"
            if key not in seen:
                seen.add(key)
                unique_events.append(event)

        return {
            "success": True,
            "events": unique_events,
            "total_count": len(unique_events),
            "source_counts": source_counts,
            "errors": errors,
        }

    def validate_input(self, input_data: Dict[str, Any]) -> None:
        required_fields = ["location"]
        for field in required_fields:
            if field not in input_data:
                raise ValueError(f"Missing required field: {field}")
            if not input_data[field] or not isinstance(input_data[field], str):
                raise ValueError(f"Field {field} must be a non-empty string")

# Global instance for easy access
family_search = FamilyEventSearchTool()

# Convenience functions
def search_family_events(location: str, **kwargs):
    """Search for family-focused events."""
    return family_search.search_events(location, **kwargs) 