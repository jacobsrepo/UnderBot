"""
Cortex Live Web Surfer — Real-Time Search & Page Content Extraction
Uses DuckDuckGo HTML Search + BeautifulSoup page scraping for fresh, live data.
"""

import json
import re
import urllib.request
import urllib.parse
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup


class WebSurfer:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

    async def surf(self, query: str) -> Dict[str, Any]:
        """Search the live web, fetch top result page content, and return structured data."""
        query_clean = query.strip()
        lower_q = query_clean.lower()

        # Strip common prefixes
        clean_topic = re.sub(
            r'^(image of|picture of|photo of|search for|search|browse|lookup|what is|who is|tell me about|find|look up)\s+',
            '', query_clean, flags=re.IGNORECASE
        ).strip()
        if not clean_topic:
            clean_topic = query_clean

        # If it's a direct URL, fetch and parse that page
        if lower_q.startswith("http://") or lower_q.startswith("https://"):
            return await self._fetch_and_extract_page(query_clean)

        # --- Step 1: Live web search via DuckDuckGo HTML ---
        search_results = await self._ddg_html_search(clean_topic)

        if not search_results:
            # Fallback: try Wikipedia
            wiki = await self._search_wikipedia(clean_topic)
            if wiki:
                return wiki
            return self._fallback_result(clean_topic)

        # --- Step 2: Fetch actual page content from top result ---
        top_url = search_results[0]["url"]
        page_content = await self._fetch_page_text(top_url)

        # Build rich cards from search results
        cards = []
        for r in search_results[:4]:
            cards.append({
                "label": r.get("domain", "WEB")[:22],
                "val": r["title"][:55]
            })

        # Try to get a Wikipedia thumbnail image for the topic
        image_url = None
        wiki = await self._search_wikipedia(clean_topic)
        if wiki and wiki.get("image_url"):
            image_url = wiki["image_url"]

        # Build combined summary: search snippets + extracted page content
        snippet_lines = []
        for r in search_results[:3]:
            if r.get("snippet"):
                snippet_lines.append(f"• {r['title']}: {r['snippet']}")

        if page_content:
            snippet_lines.append(f"\n--- Extracted from {top_url} ---\n{page_content}")

        summary = "\n".join(snippet_lines) if snippet_lines else f"Searched the web for '{clean_topic}'."

        return {
            "url": top_url,
            "title": search_results[0]["title"],
            "badge": search_results[0].get("domain", "LIVE WEB"),
            "image_url": image_url,
            "results": search_results[:4],
            "cards": cards,
            "summary": summary
        }

    async def _ddg_html_search(self, query: str) -> List[Dict[str, Any]]:
        """Search DuckDuckGo via its HTML endpoint (POST) — returns real organic results."""
        try:
            ddg_url = "https://html.duckduckgo.com/html/"
            post_data = urllib.parse.urlencode({'q': query, 'b': ''}).encode('utf-8')
            req = urllib.request.Request(ddg_url, data=post_data, headers={
                **self.headers,
                "Content-Type": "application/x-www-form-urlencoded",
                "Referer": "https://html.duckduckgo.com/",
            })

            with urllib.request.urlopen(req, timeout=6.0) as resp:
                html = resp.read().decode('utf-8', errors='ignore')
                soup = BeautifulSoup(html, 'html.parser')

                title_links = soup.find_all('a', class_='result__a')
                snippet_links = soup.find_all('a', class_='result__snippet')

                results = []
                for i, a_tag in enumerate(title_links[:6]):
                    title = a_tag.get_text().strip()
                    href = a_tag.get('href', '')

                    # Decode DuckDuckGo redirect URL
                    if 'uddg=' in href:
                        m = re.search(r'uddg=([^&]+)', href)
                        if m:
                            href = urllib.parse.unquote(m.group(1))

                    if not href.startswith('http'):
                        continue

                    snippet = ""
                    if i < len(snippet_links):
                        snippet = snippet_links[i].get_text().strip()

                    domain = urllib.parse.urlparse(href).netloc.replace("www.", "").upper()

                    results.append({
                        "title": title,
                        "url": href,
                        "domain": domain,
                        "snippet": snippet
                    })

                return results

        except Exception as e:
            print(f"DDG HTML search error: {e}")
            return []

    async def _fetch_page_text(self, url: str, max_chars: int = 1500) -> str:
        """Fetch a URL and extract readable text content (stripped of boilerplate)."""
        try:
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=6.0) as resp:
                raw = resp.read()
                html = raw.decode('utf-8', errors='ignore')
                soup = BeautifulSoup(html, 'html.parser')

                # Remove non-content elements
                for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside',
                                 'form', 'button', 'iframe', 'noscript']):
                    tag.decompose()

                # Try to find main content area
                main = soup.find('main') or soup.find('article') or soup.find('div', role='main')
                source = main if main else soup.body if soup.body else soup

                text = source.get_text(separator='\n', strip=True)
                # Filter to meaningful lines (>30 chars, no pure nav/menu lines)
                lines = []
                for line in text.split('\n'):
                    line = line.strip()
                    if len(line) > 30:
                        lines.append(line)

                content = '\n'.join(lines)
                return content[:max_chars]

        except Exception as e:
            print(f"Page fetch error for {url}: {e}")
            return ""

    async def _fetch_and_extract_page(self, url: str) -> Dict[str, Any]:
        """Directly fetch a URL and return structured data."""
        try:
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=6.0) as resp:
                html = resp.read().decode('utf-8', errors='ignore')
                soup = BeautifulSoup(html, 'html.parser')

                title = soup.title.string.strip() if soup.title and soup.title.string else url

                # Extract og:image
                og_img = None
                img_meta = soup.find('meta', attrs={'property': 'og:image'})
                if img_meta and img_meta.get('content'):
                    og_img = img_meta['content']

                # Extract meta description
                meta_desc = ""
                desc_meta = soup.find('meta', attrs={'name': 'description'}) or soup.find('meta', attrs={'property': 'og:description'})
                if desc_meta and desc_meta.get('content'):
                    meta_desc = desc_meta['content'].strip()

                # Extract page text
                for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
                    tag.decompose()
                main = soup.find('main') or soup.find('article') or soup.body or soup
                text = main.get_text(separator='\n', strip=True)
                lines = [l.strip() for l in text.split('\n') if len(l.strip()) > 30]
                page_text = '\n'.join(lines[:30])

                domain = urllib.parse.urlparse(url).netloc.upper()

                summary = meta_desc if meta_desc else page_text[:500]

                return {
                    "url": url,
                    "title": title,
                    "badge": domain,
                    "image_url": og_img,
                    "results": [{"title": title, "url": url, "domain": domain, "snippet": summary[:200]}],
                    "cards": [
                        {"label": "HOST", "val": domain},
                        {"label": "STATUS", "val": "HTTP 200 OK"},
                    ],
                    "summary": f"{summary}\n\n--- Page Content ---\n{page_text[:1200]}"
                }
        except Exception as e:
            return {
                "url": url,
                "title": f"Error: {url}",
                "badge": "HTTP ERROR",
                "image_url": None,
                "results": [],
                "cards": [{"label": "ERROR", "val": str(e)[:50]}],
                "summary": f"Could not fetch {url}: {e}"
            }

    async def _search_wikipedia(self, topic: str) -> Optional[Dict[str, Any]]:
        """Query Wikipedia REST API for summary and thumbnail image."""
        try:
            search_url = f"https://en.wikipedia.org/w/api.php?action=opensearch&search={urllib.parse.quote(topic)}&limit=1&namespace=0&format=json"
            req = urllib.request.Request(search_url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=4.0) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                if len(data) >= 4 and data[1] and data[3]:
                    page_title = data[1][0]
                    page_url = data[3][0]

                    summary_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(page_title)}"
                    req2 = urllib.request.Request(summary_url, headers=self.headers)
                    with urllib.request.urlopen(req2, timeout=4.0) as resp2:
                        sdata = json.loads(resp2.read().decode('utf-8'))
                        extract = sdata.get("extract", "")
                        image_url = sdata.get("thumbnail", {}).get("source", None)
                        description = sdata.get("description", "Wikipedia")

                        return {
                            "url": page_url,
                            "title": page_title,
                            "badge": description.upper()[:30],
                            "image_url": image_url,
                            "results": [{"title": page_title, "url": page_url, "domain": "WIKIPEDIA", "snippet": extract[:200]}],
                            "cards": [
                                {"label": "TOPIC", "val": page_title},
                                {"label": "CATEGORY", "val": description[:35]},
                                {"label": "SOURCE", "val": "Wikipedia"}
                            ],
                            "summary": extract
                        }
        except Exception as e:
            print(f"Wikipedia error: {e}")
        return None

    def _fallback_result(self, topic: str) -> Dict[str, Any]:
        return {
            "url": f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(topic)}",
            "title": f"Web Search: {topic.title()}",
            "badge": "SEARCH",
            "image_url": None,
            "results": [],
            "cards": [{"label": "QUERY", "val": topic}, {"label": "STATUS", "val": "No results"}],
            "summary": f"No results found for '{topic}'."
        }

    async def get_live_weather(self, city: str = "") -> Dict[str, Any]:
        """Fetch live weather from wttr.in."""
        try:
            url = f"https://wttr.in/{urllib.parse.quote(city)}?format=j1" if city else "https://wttr.in/?format=j1"
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=4.0) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                current = data.get("current_condition", [{}])[0]
                area = data.get("nearest_area", [{}])[0]

                temp_c = current.get("temp_C", "--")
                desc = current.get("weatherDesc", [{}])[0].get("value", "Clear")
                humidity = current.get("humidity", "--")
                wind_kmph = current.get("windspeedKmph", "--")
                city_name = area.get("areaName", [{}])[0].get("value", "Local Area")

                return {
                    "city": city_name,
                    "temp_c": temp_c,
                    "desc": desc,
                    "humidity": humidity,
                    "wind_kmph": wind_kmph,
                    "summary": f"Currently {desc.lower()} in {city_name} at {temp_c}°C with {humidity}% humidity and winds at {wind_kmph} km/h."
                }
        except Exception:
            return {
                "city": city or "Unknown",
                "temp_c": "--",
                "desc": "Unavailable",
                "humidity": "--",
                "wind_kmph": "--",
                "summary": "Weather data temporarily unavailable."
            }
