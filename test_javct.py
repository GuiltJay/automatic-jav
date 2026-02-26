import requests
import cloudscraper
from bs4 import BeautifulSoup

url = "https://javct.net/"

try:
    print(f"Trying requests on {url}...")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    r = requests.get(url, headers=headers, timeout=10)
    print("Status:", r.status_code)
except Exception as e:
    print("Requests failed:", e)

try:
    print(f"\nTrying cloudscraper on {url}...")
    scraper = cloudscraper.create_scraper()
    r = scraper.get(url, timeout=10)
    print("Status:", r.status_code)
    soup = BeautifulSoup(r.text, "html.parser")
    print("Title:", soup.title.text if soup.title else "No title")
    print("First few links:", [a.get('href') for a in soup.find_all('a')][:5])
    
    # Try to find video cards
    print("\nLooking for video elements...")
    for el in soup.select("article")[:3]: # Common tag for cards
        print(el.text.strip()[:100].replace('\n', ' '))
        
    for el in soup.select(".video-block")[:3]: # Another common class
        print(el.text.strip()[:100].replace('\n', ' '))
except Exception as e:
    print("Cloudscraper failed:", e)
