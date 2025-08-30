from fastapi import FastAPI
from routes.events import router as events_router

app = FastAPI()
app.include_router(events_router)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "API is working"}

@app.get("/test")  
async def test_endpoint():
    print("[API] Test endpoint called")
    return {"message": "Test endpoint works"}

@app.get("/test/macaronikid")
async def test_macaronikid():
    """Test MacaroniKID tool with real data in Docker environment"""
    print("[API] MacaroniKID test endpoint called")
    
    from tools.macaronikid_events import MacaroniKIDEventsTool
    
    tool = MacaroniKIDEventsTool()
    
    # Test with Snellville (known working URL)
    test_location = "Snellville, GA"
    
    try:
        events = tool.execute(test_location)
        
        # Analyze the results
        real_events = [e for e in events if not e.get('source', '').endswith('(Mock)')]
        mock_events = [e for e in events if e.get('source', '').endswith('(Mock)')]
        
        return {
            "success": True,
            "location": test_location,
            "url": tool.location_urls.get(test_location),
            "total_events": len(events),
            "real_events": len(real_events),
            "mock_events": len(mock_events),
            "playwright_working": len(real_events) > 0,
            "events": events[:5],  # Return first 5 events for preview
            "message": "🎉 Real MacaroniKID events!" if len(real_events) > 0 else "⚠️ Only mock events returned"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "location": test_location,
            "message": "❌ MacaroniKID test failed"
        }

@app.get("/test/playwright")
async def test_playwright():
    """Test if Playwright is working in Docker environment"""
    print("[API] Playwright test endpoint called")
    
    try:
        from playwright.async_api import async_playwright
        
        async with async_playwright() as p:
            try:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto("https://example.com")
                title = await page.title()
                await browser.close()
                
                return {
                    "success": True,
                    "message": "✅ Playwright working!",
                    "test_title": title,
                    "playwright_available": True
                }
            except Exception as e:
                return {
                    "success": False,
                    "message": f"❌ Playwright browser error: {str(e)}",
                    "playwright_available": True,
                    "browser_error": str(e)
                }
                
    except ImportError as e:
        return {
            "success": False,
            "message": f"❌ Playwright not installed: {str(e)}",
            "playwright_available": False,
            "import_error": str(e)
        }