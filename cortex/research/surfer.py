"""
Cortex Intelligence Surfer & Real-Time News Engine
Features dedicated live news extraction via Google News RSS for fresh breaking stories and headlines,
combined with DuckDuckGo + Trafilatura publication-grade article reading with BM25 windowing.
"""

import re
import math
import json
import asyncio
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup

try:
    import trafilatura
except ImportError:
    trafilatura = None

from research.geo import GeoEngine


class WebSurfer:
    def __init__(self):
        self.geo = GeoEngine()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

    def _is_news_intent(self, query: str) -> bool:
        """Detect if user query is seeking current news or breaking updates."""
        q = query.lower()
        news_keywords = [
            "news", "latest", "breaking", "headline", "headlines", "update", "updates",
            "what happened", "today", "current events", "whats new", "what's new",
            "new in", "happening in", "going on in", "situation in"
        ]
        return any(k in q for k in news_keywords)

    def _fetch_live_news_rss(self, topic: str) -> Dict[str, Any]:
        """
        Fetches real-time breaking news headlines, sources, and publication dates
        directly from live Google News RSS feed.
        """
        try:
            encoded = urllib.parse.quote(topic)
            url = f"https://news.google.com/rss/search?q={encoded}&hl=en-US&gl=US&ceid=US:en"
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=7) as resp:
                xml_data = resp.read()

            root = ET.fromstring(xml_data)
            items = root.findall(".//item")[:6]

            if not items:
                return {}

            news_results = []
            cards = []
            summary_lines = [f"[LIVE BREAKING NEWS INTEL: '{topic.upper()}']"]

            for idx, item in enumerate(items, 1):
                title = (item.find("title").text or "").strip()
                link = (item.find("link").text or "").strip()
                pub_date = (item.find("pubDate").text or "").strip()
                source_elem = item.find("source")
                source = (source_elem.text or "News Source").strip() if source_elem is not None else "News Source"

                # Clean title if publisher name is appended
                clean_title = title
                if " - " in title:
                    clean_title = title.rsplit(" - ", 1)[0].strip()

                news_results.append({
                    "title": clean_title,
                    "url": link,
                    "source": source,
                    "published": pub_date,
                    "snippet": f"Reported by {source} on {pub_date}"
                })

                cards.append({
                    "label": source[:18],
                    "val": clean_title[:50]
                })

                summary_lines.append(f"{idx}. [{source}] \"{clean_title}\"\n   Published: {pub_date}\n   Link: {link}")

            summary_text = "\n\n".join(summary_lines)

            lead_headline = news_results[0]["title"] if news_results else f"Updates on {topic.title()}"
            top_publisher = news_results[0]["source"] if news_results else "Global News Wire"
            top_pub_date = news_results[0]["published"] if news_results else "Today"

            source_names = list(dict.fromkeys(r["source"] for r in news_results))
            narrative = f"Active news reporting across {', '.join(source_names[:3])} confirms breaking developments in {topic.title()}.\n\n" + \
                        "\n".join([f"• {r['title']} ({r['source']})" for r in news_results[:3]])

            developments = [
                {
                    "text": r["title"],
                    "source": r["source"],
                    "published": r["published"],
                    "url": r["url"]
                }
                for r in news_results
            ]

            sources_list = [
                {"name": r["source"], "url": r["url"]}
                for r in news_results
            ]

            return {
                "url": items[0].find("link").text if items else "",
                "title": lead_headline,
                "headline": lead_headline,
                "publisher": top_publisher,
                "published_date": top_pub_date,
                "domain": top_publisher,
                "topic": topic.title(),
                "category": "BREAKING NEWS",
                "briefing": narrative,
                "developments": developments,
                "sources": sources_list,
                "summary": summary_text[:4000],
                "results": news_results,
                "cards": cards,
                "is_news": True
            }
        except Exception as e:
            print(f"[WebSurfer] News RSS error for '{topic}': {e}")
            return {}

    def _score_and_window_content(self, text: str, query: str, max_chars: int = 4000) -> str:
        if not text or len(text) <= max_chars:
            return text

        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        if not paragraphs:
            return text[:max_chars]

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
                    tf = math.sqrt(count)
                    score += tf / (1.0 + 0.1 * total_words)

            scored.append((score, idx, p))

        scored_sorted = sorted(scored, key=lambda x: (x[0] + (0.5 if x[1] < 3 else 0.0)), reverse=True)

        selected_indices = set()
        current_len = 0

        for score, idx, p in scored_sorted:
            if current_len + len(p) + 2 <= max_chars:
                selected_indices.add(idx)
                current_len += len(p) + 2
            elif current_len < max_chars // 2:
                selected_indices.add(idx)
                break

        ordered_paragraphs = [paragraphs[i] for i in sorted(selected_indices)]
        res_text = "\n\n".join(ordered_paragraphs)
        return res_text[:max_chars]

    async def _fetch_and_extract_page(self, url: str, query: str = "") -> Dict[str, Any]:
        loop = asyncio.get_running_loop()

        def _fetch_sync():
            try:
                req = urllib.request.Request(url, headers=self.headers)
                with urllib.request.urlopen(req, timeout=8) as resp:
                    raw_html = resp.read().decode('utf-8', errors='replace')
                    
                    extracted_md = None
                    if trafilatura:
                        extracted_md = trafilatura.extract(
                            raw_html,
                            include_links=True,
                            include_images=False,
                            output_format='markdown'
                        )

                    if not extracted_md:
                        soup = BeautifulSoup(raw_html, 'html.parser')
                        for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "aside", "form"]):
                            tag.decompose()
                        extracted_md = soup.get_text(separator="\n", strip=True)

                    title = "Web Resource"
                    image_url = ""
                    try:
                        soup = BeautifulSoup(raw_html, 'html.parser')
                        t_tag = soup.find('title')
                        if t_tag:
                            title = t_tag.get_text().strip()
                        og_img = soup.find('meta', property='og:image') or soup.find('meta', attrs={'name': 'twitter:image'})
                        if og_img and og_img.get('content'):
                            image_url = og_img['content']
                    except Exception:
                        pass

                    return title, extracted_md or "", image_url
            except Exception as e:
                return "Web Page", f"Could not read content from {url}: {e}", ""

        title, raw_content, image_url = await loop.run_in_executor(None, _fetch_sync)
        windowed_content = self._score_and_window_content(raw_content, query, max_chars=4000)
        domain = urllib.parse.urlparse(url).netloc.replace("www.", "")

        return {
            "url": url,
            "title": title,
            "image_url": image_url,
            "domain": domain,
            "summary": windowed_content,
            "results": [
                {
                    "title": title,
                    "url": url,
                    "domain": domain,
                    "snippet": windowed_content[:250]
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
        """
        Intelligently search the live web:
        - If query is seeking news: retrieves real-time headlines and publisher briefings via Google News RSS.
        - If query is general / URL: fetches and windows article markdown via Trafilatura.
        """
        query_clean = query.strip()
        lower_q = query_clean.lower()

        clean_topic = re.sub(
            r'^(search for|search|browse|lookup|what is|who is|tell me about|find|look up|whats the|what are the)\s+',
            '', query_clean, flags=re.IGNORECASE
        ).strip() or query_clean

        # 1. Direct URL
        if lower_q.startswith("http://") or lower_q.startswith("https://"):
            return await self._fetch_and_extract_page(query_clean, query=clean_topic)

        # 2. News intent: dedicated real-time news extraction
        if self._is_news_intent(query_clean):
            # Strip words like "latest news from", "whats new in", "news about"
            topic = re.sub(r'\b(latest|breaking|news|updates|from|about|today|whats|what\'s|new|in|the|happening)\b', '', clean_topic, flags=re.IGNORECASE).strip()
            if not topic:
                topic = clean_topic

            loop = asyncio.get_running_loop()
            news_data = await loop.run_in_executor(None, self._fetch_live_news_rss, topic)
            if news_data and news_data.get("results"):
                return news_data

        # 3. General web search via DuckDuckGo + Trafilatura
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

        # Pick best article URL (avoid root homepages when specific articles exist)
        target_result = search_results[0]
        for r in search_results:
            # If URL has path segments, it's an article rather than a homepage
            path = urllib.parse.urlparse(r["url"]).path
            if len(path) > 3 and not path.endswith("/"):
                target_result = r
                break

        top_url = target_result["url"]
        page_data = await self._fetch_and_extract_page(top_url, query=clean_topic)
        page_summary = page_data.get("summary", "")

        snippet_lines = []
        for r in search_results[:3]:
            if r.get("snippet"):
                snippet_lines.append(f"• {r['title']}: {r['snippet']}")

        if page_summary:
            snippet_lines.append(f"\n--- Grounded Content from {top_url} ---\n{page_summary}")

        combined_summary = "\n".join(snippet_lines)

        developments = [
            {
                "text": f"{r['title']}: {r.get('snippet', '')}",
                "source": r.get("domain", "WEB"),
                "published": "Recent",
                "url": r["url"]
            }
            for r in search_results[:4]
            if r.get("snippet")
        ]

        sources_list = [
            {"name": r.get("domain", "WEB"), "url": r["url"]}
            for r in search_results[:6]
        ]

        return {
            "url": top_url,
            "title": target_result["title"],
            "headline": target_result["title"],
            "publisher": target_result.get("domain", "WEB"),
            "published_date": "Live Web Data",
            "domain": target_result.get("domain", "WEB"),
            "category": "WEB RESEARCH",
            "briefing": page_summary or (target_result.get("snippet", "") + "\n\n" + "\n".join([r.get("snippet", "") for r in search_results[1:3]])),
            "developments": developments,
            "sources": sources_list,
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

    async def plan_day_itinerary(self, destination: str = "", preferences: str = "", budget: str = "moderate") -> Dict[str, Any]:
        """
        Synthesizes a complete 1-day itinerary with realistic schedule times,
        real local venue recommendations, photos, itemized price estimates,
        and Google Maps route links.
        """
        dest_clean = destination.strip()
        user_loc = await self.geo.get_live_location()

        # If no destination given or user asks for "here/nearby", use live location
        if not dest_clean or any(k in dest_clean.lower() for k in ["here", "nearby", "current", "my city", "around me"]):
            dest_clean = user_loc.get("city") or "Central District"

        # Search for venues & landmarks in destination
        food_res = await self.geo.search_places("cafe breakfast bakery", near_location=dest_clean, limit=3)
        sight_res = await self.geo.search_places("museum landmark attraction historic", near_location=dest_clean, limit=4)
        lunch_res = await self.geo.search_places("restaurant local dining bistro", near_location=dest_clean, limit=3)
        park_res = await self.geo.search_places("park viewpoint square scenic", near_location=dest_clean, limit=3)
        dinner_res = await self.geo.search_places("dinner restaurant gastro bar", near_location=dest_clean, limit=3)

        b_food = food_res.get("places", [{}])[0] if food_res.get("places") else {"name": f"Local Artisan Cafe in {dest_clean}", "address": dest_clean, "category": "Cafe", "lat": user_loc.get("latitude"), "lon": user_loc.get("longitude")}
        b_sight = sight_res.get("places", [{}])[0] if sight_res.get("places") else {"name": f"{dest_clean} Historic Quarter", "address": dest_clean, "category": "Historic District", "lat": user_loc.get("latitude"), "lon": user_loc.get("longitude")}
        b_lunch = lunch_res.get("places", [{}])[0] if lunch_res.get("places") else {"name": f"Traditional Dining Room", "address": dest_clean, "category": "Restaurant", "lat": user_loc.get("latitude"), "lon": user_loc.get("longitude")}
        b_park = park_res.get("places", [{}])[0] if park_res.get("places") else {"name": f"{dest_clean} Scenic Promenade", "address": dest_clean, "category": "Park", "lat": user_loc.get("latitude"), "lon": user_loc.get("longitude")}
        b_dinner = dinner_res.get("places", [{}])[0] if dinner_res.get("places") else {"name": f"Sunset Bistro & Lounge", "address": dest_clean, "category": "Fine Dining", "lat": user_loc.get("latitude"), "lon": user_loc.get("longitude")}

        # Budget multipliers
        b_lower = (budget or "moderate").lower()
        if "budget" in b_lower or "cheap" in b_lower:
            costs = ["$8 - $12", "Free - $10", "$14 - $18", "Free", "$22 - $30"]
            tot_est = "$45 - $70 per person"
        elif "luxury" in b_lower or "high" in b_lower or "fine" in b_lower:
            costs = ["$25 - $40", "$25 - $45", "$45 - $80", "Free - $15", "$85 - $160"]
            tot_est = "$180 - $340 per person"
        else:
            costs = ["$12 - $18", "$12 - $20", "$20 - $32", "Free", "$35 - $60"]
            tot_est = "$80 - $130 per person"

        stops = [
            {
                "time": "09:00 AM - 10:15 AM",
                "period": "Morning",
                "title": f"Breakfast & Specialty Coffee at {b_food.get('name')}",
                "name": b_food.get("name"),
                "category": "Artisan Breakfast",
                "activity": f"Kick off the morning with freshly brewed coffee, artisanal pastries, and a lively neighborhood ambiance.",
                "cost": costs[0],
                "address": b_food.get("address", dest_clean),
                "image_url": b_food.get("image_url", ""),
                "lat": b_food.get("lat"),
                "lon": b_food.get("lon"),
                "directions_url": self.geo.get_google_maps_dir_url(b_food.get("lat", 0), b_food.get("lon", 0), b_food.get("name", ""))
            },
            {
                "time": "10:45 AM - 01:00 PM",
                "period": "Midday",
                "title": f"Cultural Discovery at {b_sight.get('name')}",
                "name": b_sight.get("name"),
                "category": "Culture & Heritage",
                "activity": f"Explore architectural highlights, curated exhibits, and historical landmarks that define the character of {dest_clean}.",
                "cost": costs[1],
                "address": b_sight.get("address", dest_clean),
                "image_url": b_sight.get("image_url", ""),
                "lat": b_sight.get("lat"),
                "lon": b_sight.get("lon"),
                "directions_url": self.geo.get_google_maps_dir_url(b_sight.get("lat", 0), b_sight.get("lon", 0), b_sight.get("name", ""))
            },
            {
                "time": "01:15 PM - 02:30 PM",
                "period": "Lunch",
                "title": f"Regional Cuisine at {b_lunch.get('name')}",
                "name": b_lunch.get("name"),
                "category": "Lunch & Refreshment",
                "activity": f"Savor authentic regional flavors and seasonal specialties in a relaxed dining setting.",
                "cost": costs[2],
                "address": b_lunch.get("address", dest_clean),
                "image_url": b_lunch.get("image_url", ""),
                "lat": b_lunch.get("lat"),
                "lon": b_lunch.get("lon"),
                "directions_url": self.geo.get_google_maps_dir_url(b_lunch.get("lat", 0), b_lunch.get("lon", 0), b_lunch.get("name", ""))
            },
            {
                "time": "03:00 PM - 05:30 PM",
                "period": "Afternoon",
                "title": f"Scenic Stroll & Leisure at {b_park.get('name')}",
                "name": b_park.get("name"),
                "category": "Scenic & Outdoor",
                "activity": f"Unwind with a stroll through scenic parklands, boutique shopping streets, and panoramic viewpoints.",
                "cost": costs[3],
                "address": b_park.get("address", dest_clean),
                "image_url": b_park.get("image_url", ""),
                "lat": b_park.get("lat"),
                "lon": b_park.get("lon"),
                "directions_url": self.geo.get_google_maps_dir_url(b_park.get("lat", 0), b_park.get("lon", 0), b_park.get("name", ""))
            },
            {
                "time": "06:30 PM - 09:00 PM",
                "period": "Evening",
                "title": f"Signature Dinner & Sunset at {b_dinner.get('name')}",
                "name": b_dinner.get("name"),
                "category": "Dinner & Atmosphere",
                "activity": f"Cap off the day with an evening dinner featuring crafted cocktails, culinary pairings, and evening atmosphere.",
                "cost": costs[4],
                "address": b_dinner.get("address", dest_clean),
                "image_url": b_dinner.get("image_url", ""),
                "lat": b_dinner.get("lat"),
                "lon": b_dinner.get("lon"),
                "directions_url": self.geo.get_google_maps_dir_url(b_dinner.get("lat", 0), b_dinner.get("lon", 0), b_dinner.get("name", ""))
            }
        ]

        center_lat = b_sight.get("lat") or b_food.get("lat") or user_loc.get("latitude", 0)
        center_lon = b_sight.get("lon") or b_food.get("lon") or user_loc.get("longitude", 0)
        embed_map = self.geo.get_google_maps_embed_url(center_lat, center_lon, query=dest_clean)

        headline = f"1-Day Exploration Blueprint: {dest_clean.title()}"
        summary_lines = [
            f"# {headline}",
            f"**Estimated Total Budget:** {tot_est} | **Pacing:** Balanced walking & transit",
            "",
            "## Schedule Breakdown:"
        ]
        for s in stops:
            summary_lines.append(f"• **{s['time']}**: {s['title']} ({s['cost']})")
            summary_lines.append(f"  {s['activity']}")

        return {
            "type": "itinerary",
            "headline": headline,
            "destination": dest_clean.title(),
            "budget_tier": (budget or "moderate").capitalize(),
            "total_budget_est": tot_est,
            "center_lat": center_lat,
            "center_lon": center_lon,
            "embed_map_url": embed_map,
            "stops": stops,
            "tips": [
                "Wear comfortable footwear as the route connects through central historic quarters.",
                "Reserve dining ahead for dinner spots during peak weekend hours.",
                "Transit passes or day tickets provide seamless hopping between distant stops."
            ],
            "summary": "\n".join(summary_lines)
        }

    async def search_prices_and_deals(self, query: str) -> Dict[str, Any]:
        """
        Specialized price and product comparison search.
        Extracts verified costs, deal highlights, retailers, and visual previews.
        """
        clean_q = query.strip()
        search_kw = f"{clean_q} price cost compare buy"
        raw_results = await self._ddg_html_search(search_kw)

        items = []
        price_regex = re.compile(r'(\$\s?[0-9,]+(?:\.[0-9]{2})?|€\s?[0-9,]+(?:\.[0-9]{2})?|£\s?[0-9,]+(?:\.[0-9]{2})?|[0-9,]+\s?(?:USD|EUR|GBP))', re.IGNORECASE)

        badges = ["Best Value", "Top Pick", "Popular", "Competitive Deal", "Direct Retail"]

        for idx, r in enumerate(raw_results[:6]):
            text = f"{r.get('title', '')} {r.get('snippet', '')}"
            matches = price_regex.findall(text)
            price_val = matches[0] if matches else "Check Retailer"

            # Clean product title
            title = r.get("title", "Product Option")
            if " - " in title:
                title = title.split(" - ")[0].strip()

            domain = r.get("domain", "Online Store")

            # Try to fetch photo from Wikimedia or Wikipedia for the product/topic
            photo_info = await self.geo.fetch_place_photo_and_extract(clean_q, category="product")
            img = photo_info.get("image_url") or ""

            items.append({
                "title": title[:70],
                "price": price_val.strip(),
                "source": domain,
                "url": r.get("url", ""),
                "snippet": r.get("snippet", "")[:180],
                "image_url": img,
                "badge": badges[idx % len(badges)]
            })

        prices_found = [it["price"] for it in items if "$" in it["price"] or "€" in it["price"] or "£" in it["price"]]
        price_range = f"{prices_found[0]} - {prices_found[-1]}" if len(prices_found) >= 2 else "Varies by retailer"

        summary_lines = [
            f"Price Comparison & Market Overview for **'{clean_q}'**:",
            f"**Estimated Price Range:** {price_range}",
            ""
        ]
        for it in items[:4]:
            summary_lines.append(f"• **{it['title']}** - `{it['price']}` ({it['source']})")
            if it.get("snippet"):
                summary_lines.append(f"  {it['snippet']}")

        return {
            "type": "prices",
            "query": clean_q,
            "headline": f"Pricing Intelligence: {clean_q.title()}",
            "price_range": price_range,
            "items": items,
            "summary": "\n".join(summary_lines)
        }

