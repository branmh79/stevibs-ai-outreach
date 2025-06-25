from typing import Dict, Any, List
from .base_tool import BaseTool
from .contact_scraper import ContactScraperTool

class FamilyEventSearchTool(BaseTool):
    """
    Tool specifically designed for finding family-focused events for SteviB's franchise owners.
    Targets families with kids 7-18 years old.
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
        self.tools = {
            "scraper": ContactScraperTool()
        }
        
        # Family-focused search categories
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
            search_radius = input_data.get("search_radius", 5000)
            
            all_events = []
            source_counts = {}
            errors = []
            
            # Search each family-focused category
            for category in self.family_categories:
                try:
                    tool = self.tools["scraper"]
                    
                    tool_input = {
                        "location": location,
                        "query": category,
                        "use_mock": use_mock,
                        "search_radius": search_radius
                    }
                    
                    result = tool(tool_input)
                    
                    if result["success"]:
                        # Convert Place objects to event format
                        events = []
                        for place in result["places"]:
                            # Filter for family-relevant results
                            if self._is_family_relevant(place, category):
                                events.append({
                                    "title": place.get("name"),
                                    "description": place.get("description"),
                                    "date": None,
                                    "website": place.get("website"),
                                    "contact_email": place.get("contact_email"),
                                    "phone": place.get("phone_number"),
                                    "address": place.get("address"),
                                    "source": "family_scraper",
                                    "category": category
                                })
                        
                        all_events.extend(events)
                        source_counts[category] = len(events)
                    else:
                        errors.append(f"{category}: {result.get('error', 'Unknown error')}")
                        source_counts[category] = 0
                        
                except Exception as e:
                    errors.append(f"{category}: {str(e)}")
                    source_counts[category] = 0
            
            # Remove duplicates and sort by relevance
            unique_events = self._deduplicate_and_rank_events(all_events)
            
            return {
                "success": True,
                "events": unique_events,
                "total_count": len(unique_events),
                "source_counts": source_counts,
                "errors": errors
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

    def _is_family_relevant(self, place: Dict[str, Any], category: str) -> bool:
        """Filter places to ensure they're relevant for families with kids 7-18."""
        name = place.get("name", "").lower()
        description = place.get("description", "").lower()
        
        # Keywords that indicate family/youth focus
        family_keywords = [
            "youth", "teen", "child", "kid", "family", "summer camp", "after school",
            "recreation", "sports", "community", "school", "ymca", "boys girls",
            "parks", "activities", "program", "club"
        ]
        
        # Keywords that indicate it's NOT family-focused
        exclude_keywords = [
            "adult", "senior", "elderly", "retirement", "nursing", "bar", "pub",
            "nightclub", "casino", "gambling", "alcohol", "21+", "adults only"
        ]
        
        # Check for family keywords
        has_family_focus = any(keyword in name or keyword in description for keyword in family_keywords)
        
        # Check for exclusion keywords
        has_exclusion = any(keyword in name or keyword in description for keyword in exclude_keywords)
        
        return has_family_focus and not has_exclusion

    def _deduplicate_and_rank_events(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicates and rank by relevance to families."""
        seen = set()
        unique_events = []
        
        for event in events:
            title = event.get("title", "").lower().strip()
            website = event.get("website", "")
            website_str = str(website).lower().strip() if website else ""
            
            # Create a unique key
            key = f"{title}|{website_str}"
            
            if key not in seen:
                seen.add(key)
                unique_events.append(event)
        
        # Sort by relevance (you can enhance this ranking logic)
        def relevance_score(event):
            title = event.get("title", "").lower()
            description = event.get("description", "").lower()
            
            # Higher scores for more relevant keywords
            score = 0
            high_relevance = ["summer camp", "after school", "youth", "teen", "family"]
            medium_relevance = ["recreation", "sports", "community", "school"]
            
            for keyword in high_relevance:
                if keyword in title or keyword in description:
                    score += 3
            
            for keyword in medium_relevance:
                if keyword in title or keyword in description:
                    score += 1
            
            return score
        
        unique_events.sort(key=relevance_score, reverse=True)
        return unique_events

# Global instance for easy access
family_search = FamilyEventSearchTool()

# Convenience functions
def search_family_events(location: str, **kwargs):
    """Search for family-focused events."""
    return family_search.search_events(location, **kwargs) 