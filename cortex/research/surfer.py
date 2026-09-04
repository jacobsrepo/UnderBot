"""
Cortex Hardened Web Surfer & Content Extraction Engine
Uses DuckDuckGo HTML search + Trafilatura publication-grade reader with BM25/keyword density windowing.
Enforces a hard 4,000-character ceiling to prevent prompt context bloat.
"""

import re
import math
import asyncio
import urllib.request
import urllib.parse
import json
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup

try:
    import trafilatura
except ImportError:
    trafilatura = None


class WebSurfer:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

    def _score_and_window_content(self, text: str, query: str, max_chars: int = 4000) -> str:
        """
        BM25-style keyword density windowing:
        Splits extracted markdown into paragraphs, scores relevance to query terms,
        and selects top paragraphs within max_chars ceiling.
        """
        if not text or len(text) <= max_chars:
            return text

        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        if not paragraphs:
            return text[:max_chars]

        # Extract search terms
        terms = set(re.findall(r"\w{3,}", query.lower()))
        if not terms:
            return "\n\n".join(paragraphs)[:max_chars]

        scored = []
        for idx, p in enumerate(paragraphs):
            p_lower = p.lower()
            score = 0.0
            words = re.findall(r"\w+", p_lower)
            total_words = max(len(words), 1)

            for t in terms:
                count = p_lower.count(t)
                if count > 0:
                    # Term frequency with diminishing returns
                    tf = math.sqrt(count)
                    score += tf / (1.0 + 0.1 * total_words)

            scored.append((score, idx, p))

        # Sort paragraphs by score, keeping the most relevant
        # Favor early paragraphs slightly
        scored_sorted = sorted(scored, key=lambda x: (x[0] + (0.5 if x[1] < 3 else 0.0)), reverse=True)

        selected_indices = set()
        current_len = 0

        for score, idx, p in scored_sorted:
            if current_len + len(p) + 2 <= max_chars:
                selected_indices.add(idx)
                current_len += len(p) + 2
            elif current_len < max_chars // 2:
                # Add truncated
                remaining = max_chars - current_len - 5
                if remaining > 100:
                    selected_indices.add(idx)
                break

        # Re-assemble in original document order
        ordered_paragraphs = [paragraphs[i] for i in sorted(selected_indices)]
        res_text = "\n\n".join(ordered_paragraphs)
        return res_text[:max_chars]

    async def _fetch_and_extract_page(self, url: str, query: str = "") -> Dict[str, Any]:
        """Fetches raw HTML and extracts clean publication-grade Markdown using trafilatura."""
        loop = asyncio.get_running_loop()

        def _fetch_sync():
            try:
                req = urllib.request.Request(url, headers=self.headers)
                with urllib.request.urlopen(req, timeout=8) as resp:
                    raw_html = resp.read().decode('utf-8', errors='replace')
                    
                    # Primary: Trafilatura reader
                    extracted_md = None
                    if trafilatura:
                        extracted_md = trafilatura.extract(
                            raw_html,
                            include_links=True,
                            include_images=False,
                            output_format='markdown'
                        )

                    # Fallback: BeautifulSoup text extraction
                    if not extracted_md:
                        soup = BeautifulSoup(raw_html, 'html.parser')
                        for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "aside", "form"]):
                            tag.decompose()
                        extracted_md = soup.get_text(separator="\n", strip=True)

                    title = "Web Resource"
                    try:
                        soup = BeautifulSoup(raw_html, 'html.parser')
                        t_tag = soup.find('title')
                        if t_tag:
                            title = t_tag.get_text().strip()
                    except Exception:
                        pass

                    return title, extracted_md or ""
            except Exception as e:
                print(f"[WebSurfer] Fetch error for {url}: {e}")
                return "Error Fetching URL", f"Could not read content from {url}: {e}"

        title, raw_content = await loop.run_in_executor(None, _fetch_sync)
        windowed_content = self._score_and_window_content(raw_content, query, max_chars=4000)

        domain = urllib.parse.urlparse(url).netloc.replace("www.", "")

        return {
            "url": url,
            "title": title,
            "domain": domain,
            "summary": windowed_content,
            "results": [
                {
                    "title": title,
                    "url": url,
                    "domain": domain,
                    "snippet": windowed_content[:200]
                }
            ],
            "cards": [
                {"label": "SOURCE", "val": domain},
                {"label": "STATUS", "val": "Extracted with Trafilatura"}
            ]
        }

    async def _ddg_html_search(self, query: str) -> List[Dict[str, str]]:
        loop = asyncio.get_running_loop()

        def _search_sync():
            results = []
            try:
                encoded = urllib.parse.urlencode({"q": query, "b": ""})
                req = urllib.request.Request(
                    "https://html.duckduckgo.com/html/",
                    data=encoded.encode("utf-8"),
                    headers={
                        **self.headers,
                        "Content-Type": "application/x-www-form-urlencoded"
                    }
                )
                with urllib.request.urlopen(req, timeout=7) as resp:
                    html_text = resp.read().decode("utf-8", errors="replace")

                soup = BeautifulSoup(html_text, "html.parser")
                for r in soup.find_all("div", class_="result"):
                    title_elem = r.find("a", class_="result__a")
                    snippet_elem = r.find("a", class_="result__snippet") or r.find("div", class_="result__snippet")
                    url_elem = r.find("a", class_="result__url")

                    if title_elem and title_elem.get_text():
                        title = title_elem.get_text().strip()
                        raw_href = title_elem.get("href", "")

                        parsed_url = raw_href
                        if "uddg=" in raw_href:
                            try:
                                actual = urllib.parse.parse_qs(urllib.parse.urlparse(raw_href).query).get("uddg")
                                if actual:
                                    parsed_url = actual[0]
                            except Exception:
                                pass

                        snippet = snippet_elem.get_text().strip() if snippet_elem else ""
                        domain = urllib.parse.urlparse(parsed_url).netloc.replace("www.", "")

                        if parsed_url.startswith("http") and domain:
                            results.append({
                                "title": title,
                                "url": parsed_url,
                                "snippet": snippet,
                                "domain": domain
                            })
                            if len(results) >= 5:
                                break
            except Exception as e:
                print(f"[WebSurfer] Search error: {e}")

            return results

        return await loop.run_in_executor(None, _search_sync)

    async def surf(self, query: str) -> Dict[str, Any]:
        """Search the live web, fetch top result with trafilatura, window content, and return structured intel."""
        query_clean = query.strip()
        lower_q = query_clean.lower()

        clean_topic = re.sub(
            r'^(search for|search|browse|lookup|what is|who is|tell me about|find|look up)\s+',
            '', query_clean, flags=re.IGNORECASE
        ).strip() or query_clean

        if lower_q.startswith("http://") or lower_q.startswith("https://"):
            return await self._fetch_and_extract_page(query_clean, query=clean_topic)

        search_results = await self._ddg_html_search(clean_topic)

        if not search_results:
            return {
                "url": "",
                "title": f"Search: {clean_topic}",
                "domain": "WEB",
                "summary": f"No immediate live web search results found for '{clean_topic}'.",
                "results": [],
                "cards": []
            }

        top_result = search_results[0]
        top_url = top_result["url"]

        # Extract top page text using trafilatura
        page_data = await self._fetch_and_extract_page(top_url, query=clean_topic)
        page_summary = page_data.get("summary", "")

        # Assemble search summary
        snippet_lines = []
        for r in search_results[:3]:
            if r.get("snippet"):
                snippet_lines.append(f"• {r['title']}: {r['snippet']}")

        if page_summary:
            snippet_lines.append(f"\n--- Grounded Content from {top_url} ---\n{page_summary}")

        combined_summary = "\n".join(snippet_lines)

        return {
            "url": top_url,
            "title": top_result["title"],
            "domain": top_result.get("domain", "WEB"),
            "summary": combined_summary[:4000],
            "results": search_results,
            "cards": [
                {"label": r.get("domain", "WEB")[:18], "val": r["title"][:45]}
                for r in search_results[:4]
            ]
        }

    async def get_live_weather(self, city: str = "") -> Dict[str, Any]:
        city_clean = city.strip() or "auto"
        loop = asyncio.get_running_loop()

        def _fetch_weather_sync():
            try:
                url = f"https://wttr.in/{urllib.parse.quote(city_clean)}?format=j1"
                req = urllib.request.Request(url, headers={"User-Agent": "curl/7.68.0"})
                with urllib.request.urlopen(req, timeout=5) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    curr = data.get("current_condition", [{}])[0]
                    area = data.get("nearest_area", [{}])[0]
                    loc = area.get("areaName", [{}])[0].get("value", city_clean)
                    temp_c = curr.get("temp_C", "N/A")
                    desc = curr.get("weatherDesc", [{}])[0].get("value", "Clear")
                    humidity = curr.get("humidity", "N/A")
                    return {
                        "location": loc,
                        "temperature_c": temp_c,
                        "condition": desc,
                        "humidity": f"{humidity}%",
                        "summary": f"Current weather in {loc}: {temp_c}°C, {desc}, humidity {humidity}%."
                    }
            except Exception as e:
                return {"summary": f"Could not retrieve weather: {e}"}

        return await loop.run_in_executor(None, _fetch_weather_sync)
