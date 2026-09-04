---
name: Web Intelligence
description: Perform live internet searches, scrape and extract publication-grade content via Trafilatura, and retrieve fresh data.
tools: search_or_browse_web, get_live_weather
---

# Web Intelligence Skill

Use `search_or_browse_web` whenever the user asks for:
- Fresh real-time news, documentation, specifications, or data beyond your offline training.
- Reading or summarizing a specific web link (URL).

The engine automatically fetches the webpage, cleans boilerplate via Trafilatura, applies BM25 keyword density windowing, and caps the result at 4,000 characters.
