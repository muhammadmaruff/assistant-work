import os, sys, json, datetime, urllib.request

KEY = os.environ["FIRECRAWL_API_KEY"]
urls = [u.strip() for u in open("urls.txt") if u.strip() and not u.startswith("#")]
extra = os.environ.get("EXTRA_URL", "").strip()
if extra:
    urls = [extra]

today = datetime.date.today().isoformat()
os.makedirs(f"data/{today}", exist_ok=True)

for i, url in enumerate(urls):
    req = urllib.request.Request(
        "https://api.firecrawl.dev/v1/scrape",
        data=json.dumps({"url": url, "formats": ["markdown"], "onlyMainContent": True}).encode(),
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            md = json.load(r)["data"]["markdown"]
    except Exception as e:
        print(f"GAGAL {url}: {e}", file=sys.stderr)
        continue
    with open(f"data/{today}/{i+1:02d}.md", "w") as f:
        f.write(f"<!-- sumber: {url} -->\n\n{md}")
    print(f"OK {url}")
