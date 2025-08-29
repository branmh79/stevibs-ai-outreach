# SteviB's AI Outreach

This is a local AI system to find relevant local events, summer camps, and opportunities near our restaurants using:
- Streamlit (UI) - http://localhost:8501 
- n8n (workflow trigger) - http://localhost:5678
- Ollama (LLM) - http://localhost:11434 
- Web scraping with browser automation - http://localhost:8001/events?location=Snellville (example backend)

## Quick Start

```bash
docker-compose up --build
```

The system now includes **Playwright browser automation** for enhanced Facebook events scraping that simulates real user scrolling to load more events dynamically. Everything is automatically configured in Docker - no local setup required.

## Features

- **Enhanced Facebook Events**: Browser automation with scrolling simulation loads 10x more events
- **Smart Fallbacks**: Automatically falls back to static scraping if browser automation fails  
- **Zero Configuration**: Everything works out of the box with Docker Compose
- **Production Ready**: Optimized for container environments
