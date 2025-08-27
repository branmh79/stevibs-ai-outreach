from typing import List, Dict
from models.workflow_state import WorkflowState, EventData
from tools.contact_scraper import ContactScraperTool

scraper_tool = ContactScraperTool()

async def scraping_node(state: WorkflowState) -> dict:
    """LangGraph node that scrapes contact info from URLs collected in search_results."""

    if not state.search_results or state.current_category is None:
        return {}

    urls = [item.get("website") for item in state.search_results.get("events", []) if item.get("website")]
    if not urls:
        state.source_counts[state.current_category] = 0
        return {"source_counts": state.source_counts}

    try:
        # Use async method for parallel scraping
        scrape_results: List[Dict] = await scraper_tool.scrape_contacts_from_urls_async(urls)
        state.scraped_data = scrape_results
        events: List[EventData] = []
        for item in scrape_results:
            events.append(
                EventData(
                    title=item.get("title"),
                    description=item.get("description"),
                    website=item.get("url"),
                    contact_email=item.get("contact_email"),
                    phone_number=item.get("phone_number"),
                    category=state.current_category,
                )
            )
        state.events.extend(events)
        state.source_counts[state.current_category] = len(events)
    except Exception as e:
        state.errors.append(f"Scraper error for {state.current_category}: {str(e)}")
        state.source_counts[state.current_category] = 0

    patch = {}
    if state.events:
        patch["events"] = state.events
    if state.source_counts:
        patch["source_counts"] = state.source_counts
    if state.errors:
        patch["errors"] = state.errors
    if state.is_complete:
        patch["is_complete"] = True
    return patch
