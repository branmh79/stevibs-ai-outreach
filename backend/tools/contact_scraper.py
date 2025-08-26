import os
import requests
import re
import time
from random import uniform
from typing import Dict, Any, List
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from .base_tool import BaseTool
from models.place import Place
from bs4.element import Tag

class ContactScraperTool(BaseTool):
    """
    Tool for scraping contact information from a list of URLs.
    Input: {"urls": List[str]}
    Output: {"success": bool, "results": list, "count": int, "error": str (if any)}
    """

    def __init__(self):
        super().__init__()
        self.last_request_time = 0
        self.min_delay = 1  # Minimum delay between requests in seconds
        self.visited_urls = set()
        self.visited_domains = set()

    def __call__(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            # Clear visited sets at the start of each call
            self.visited_urls.clear()
            self.visited_domains.clear()
            
            urls = input_data.get("urls", [])
            if not isinstance(urls, list) or not urls:
                raise ValueError("Input must include a non-empty list of URLs under the 'urls' key.")
            results = self.scrape_contacts_from_urls(urls)
            return {
                "success": True,
                "results": results,
                "count": len(results)
            }
        except Exception as e:
            return self.handle_error(e)

    def _rate_limited_request(self, url: str, **kwargs):
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_delay:
            time.sleep(self.min_delay - time_since_last + uniform(0, 0.5))
        self.last_request_time = time.time()
        return requests.get(url, **kwargs)

    def scrape_contacts_from_urls(self, urls: List[str]) -> List[Dict]:
        # Remove cache clearing from here since it's now done in __call__
        results = []
        for url in urls:
            if url in self.visited_urls:
                continue
            domain = urlparse(url).netloc
            if domain in self.visited_domains:
                continue
            self.visited_urls.add(url)
            self.visited_domains.add(domain)
            title, description, email, phone = self._scrape_contact_info_from_url(url)
            results.append({
                "title": title or url,
                "url": url,
                "description": description,
                "contact_email": email,
                "phone_number": phone
            })
        return results

    async def scrape_contacts_from_urls_async(self, urls: List[str]) -> List[Dict]:
        """Async wrapper to scrape a list of URLs concurrently using threads."""
        import asyncio
        from functools import partial
        loop = asyncio.get_running_loop()
        results: List[Dict] = []

        # Helper that keeps signature compatible for run_in_executor
        def _scrape(url: str):
            title, description, email, phone = self._scrape_contact_info_from_url(url)
            return {
                "title": title or url,
                "url": url,
                "description": description,
                "contact_email": email,
                "phone_number": phone,
            }

        # Use a shared ThreadPool across all calls to limit concurrency
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=10) as executor:
            tasks = [loop.run_in_executor(executor, partial(_scrape, u)) for u in urls]
            for coro in asyncio.as_completed(tasks):
                try:
                    res = await coro
                    results.append(res)
                except Exception:
                    # Skip failed URLs silently (they're logged in _scrape_contact_info_from_url)
                    pass
        return results

    def _find_contact_page_url(self, soup, base_url):
        keywords = ['contact', 'about', 'support', 'help']
        for a in soup.find_all('a', href=True):
            href = a['href'].lower()
            text = a.get_text().lower()
            if any(word in href or word in text for word in keywords):
                if href.startswith('http'):
                    # Skip login pages and avoid infinite loops
                    if 'login' in href or 'gateway' in href:
                        continue
                    print(f"Found contact/support/about/help page: {href} (from {base_url})")
                    return href
                elif href.startswith('/'):
                    from urllib.parse import urljoin
                    full_url = urljoin(base_url, href)
                    # Skip login pages and avoid infinite loops
                    if 'login' in full_url or 'gateway' in full_url:
                        continue
                    print(f"Found contact/support/about/help page: {full_url} (from {base_url})")
                    return full_url
                else:
                    from urllib.parse import urljoin
                    full_url = urljoin(base_url + '/', href)
                    # Skip login pages and avoid infinite loops
                    if 'login' in full_url or 'gateway' in full_url:
                        continue
                    print(f"Found contact/support/about/help page: {full_url} (from {base_url})")
                    return full_url
        return None

    def _scrape_contact_info_from_url(self, url: str, recursion_depth: int = 0) -> tuple[str | None, str | None, str | None, str | None]:
        # Prevent infinite recursion
        if recursion_depth > 2:
            return None, None, None, None
            
        print(f"Scraping contact info from: {url}")
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            response = self._rate_limited_request(
                url, timeout=8, headers=headers, allow_redirects=True, verify=False
            )
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            # Title and description
            title = soup.title.string.strip() if soup.title and soup.title.string else None
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            description = None
            if isinstance(meta_desc, Tag):
                content = meta_desc.get('content')
                if isinstance(content, str):
                    description = content.strip()
            # Email
            raw_emails = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", soup.text)
            print(f"Raw emails found on {url}: {raw_emails}")
            emails = []
            for e in raw_emails:
                if re.fullmatch(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", e):
                    if not any(exclude in e.lower() for exclude in [
                        'example.com', 'test.com', 'domain.com', 'noreply', 'no-reply'
                    ]):
                        emails.append(e)
            print(f"Filtered emails on {url}: {emails}")
            email = emails[0] if emails else None
            # Phone
            phones = re.findall(r"(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})", soup.text)
            print(f"Phones found on {url}: {phones}")
            phone = None
            for p in phones:
                digits = re.sub(r'\D', '', p)
                if 10 <= len(digits) <= 12:
                    phone = p
                    break
            # Try contact page if not found (with recursion limit)
            if (not email or not phone) and recursion_depth < 2:
                contact_url = self._find_contact_page_url(soup, url)
                if contact_url:
                    c_title, c_desc, c_email, c_phone = self._scrape_contact_info_from_url(contact_url, recursion_depth + 1)
                    if not email and c_email:
                        email = c_email
                    if not phone and c_phone:
                        phone = c_phone
            return title, description, email, phone
        except Exception:
            return None, None, None, None

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