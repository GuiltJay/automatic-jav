import cloudscraper
from bs4 import BeautifulSoup

scraper = cloudscraper.create_scraper()
url = "https://javct.net/amateur"
print(f"Fetching {url}")
r = scraper.get(url)
soup = BeautifulSoup(r.text, "html.parser")

# Try to find the container for videos
video_containers = soup.select(".video-block, article, .item, .col-md-3, .col-sm-6")
print(f"Found {len(video_containers)} potential video elements.")
for v in video_containers[:2]:
    print("---")
    print(v.prettify()[:500])
    
print("\nFetching models...")
r = scraper.get("https://javct.net/models")
soup = BeautifulSoup(r.text, "html.parser")
model_containers = soup.select(".item, .col-md-2, .model-block, .box")
print(f"Found {len(model_containers)} potential model elements.")
for m in model_containers[:2]:
    print("---")
    print(m.prettify()[:500])

