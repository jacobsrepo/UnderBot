import urllib.request
import urllib.parse
import re
from html import unescape

query = "latest Genshin Impact character"
# DuckDuckGo Lite endpoint
url = "https://lite.duckduckgo.com/lite/"
data = urllib.parse.urlencode({'q': query}).encode('utf-8')

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Content-Type": "application/x-www-form-urlencoded"
}

req = urllib.request.Request(url, data=data, headers=headers)
try:
    with urllib.request.urlopen(req, timeout=6) as resp:
        html = resp.read().decode('utf-8', errors='ignore')
        
        # In lite DDG:
        # <a rel="nofollow" href="..." class="result-link">Title</a>
        # <td class="result-snippet">Snippet</td>
        titles = re.findall(r'<a[^>]*class="result-link"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html)
        snippets = re.findall(r'<td class="result-snippet">\s*(.*?)\s*</td>', html, re.DOTALL)
        
        print(f"Titles found: {len(titles)}, Snippets found: {len(snippets)}")
        for i in range(min(len(titles), len(snippets), 5)):
            href, title = titles[i]
            snippet = snippets[i]
            clean_url = href
            if "uddg=" in href:
                m = re.search(r'uddg=([^&]+)', href)
                if m:
                    clean_url = urllib.parse.unquote(m.group(1))
            clean_title = unescape(re.sub(r'<[^>]+>', '', title)).strip()
            clean_snippet = unescape(re.sub(r'<[^>]+>', '', snippet)).strip()
            print("---")
            print("TITLE:", clean_title)
            print("URL:", clean_url)
            print("SNIPPET:", clean_snippet)
except Exception as e:
    print("Error:", e)
