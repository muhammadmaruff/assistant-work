import os, sys, re, json, datetime, urllib.request
from urllib.parse import urlparse

KEY = os.environ["FIRECRAWL_API_KEY"]
HOOK = os.environ.get("DRIVE_WEBHOOK_URL", "")
TOKEN = os.environ.get("DRIVE_TOKEN", "")
ONLY = os.environ.get("ONLY_MEDIA", "").strip()
DRY = os.environ.get("DRY_RUN") == "true"
TODAY = datetime.date.today().isoformat()
SKIP = re.compile(r"/(tag|tags|kategori|category|page|halaman|login|search|feed|author)(/|$)|[?&]page=|\.(jpg|png|gif|css|js)$", re.I)

os.makedirs("data", exist_ok=True)
seen = set(open("data/seen.txt").read().split()) if os.path.exists("data/seen.txt") else set()


def post(url, body, headers, timeout=120):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def fc(path, body):
    return post("https://api.firecrawl.dev/v1/" + path, body,
                {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"})


def is_article(link, host_ok):
    p = urlparse(link)
    if not p.hostname or not p.hostname.endswith(".go.id") or SKIP.search(link):
        return False
    if host_ok and p.hostname != host_ok:
        return False
    last = p.path.rstrip("/").rsplit("/", 1)[-1]
    return (last.count("-") >= 2 and len(last) >= 20) or bool(re.search(r"/\d{4,}", p.path))


def candidates(src):
    host = urlparse(src).hostname
    try:
        links = fc("scrape", {"url": src, "formats": ["links"]})["data"].get("links", [])
    except Exception as e:
        print(f"  GAGAL listing {src}: {e}", file=sys.stderr)
        return []
    out = list(dict.fromkeys(l.split("#")[0] for l in links if is_article(l, host)))
    print(f"  {src} -> {len(out)} kandidat")
    return out


def pick_urls(bucket):
    if "search" in bucket:
        try:
            res = fc("search", {"query": bucket["search"], "limit": 10, "lang": "id", "country": "id"})["data"]
        except Exception as e:
            print(f"  GAGAL search: {e}", file=sys.stderr)
            return []
        return [r["url"] for r in res if r["url"] not in seen][: bucket["count"]]
    chosen = []
    for src in bucket["sources"]:
        for l in candidates(src):
            if l not in seen and l not in chosen:
                chosen.append(l)
        if len(chosen) >= bucket["count"]:
            break
    return chosen[: bucket["count"]]


def deliver(media, files):
    if HOOK:
        try:
            r = post(HOOK, {"token": TOKEN, "media": media, "files": files}, {"Content-Type": "application/json"})
            if r.get("ok"):
                print(f"  Drive OK: {r.get('saved')} file")
                return True
            print(f"  Drive ditolak: {r}", file=sys.stderr)
        except Exception as e:
            print(f"  Drive GAGAL: {e}", file=sys.stderr)
    d = f"data/{media}/{TODAY}"
    os.makedirs(d, exist_ok=True)
    for f in files:
        open(f"{d}/{f['name']}", "w").write(f["content"])
    print(f"  Fallback: disimpan ke repo {d}")
    return False


cfg = json.load(open("sources.json"))
for media, buckets in cfg.items():
    if ONLY and ONLY != media:
        continue
    print(f"== {media}")
    files = []
    for b in buckets:
        urls = pick_urls(b)
        print(f" [{b['name']}] target {b['count']}, dapat {len(urls)}")
        if DRY:
            continue
        for u in urls:
            try:
                md = fc("scrape", {"url": u, "formats": ["markdown"], "onlyMainContent": True})["data"]["markdown"]
            except Exception as e:
                print(f"  GAGAL {u}: {e}", file=sys.stderr)
                continue
            slug = re.sub(r"[^a-z0-9]+", "-", urlparse(u).path.lower()).strip("-")[-60:] or "artikel"
            files.append({"name": f"{TODAY}_{b['name']}_{len(files)+1:02d}_{slug}.md",
                          "content": f"Sumber: {u}\nKategori: {b['name']}\n\n{md}"})
            seen.add(u)
    if files:
        deliver(media, files)

if not DRY:
    open("data/seen.txt", "w").write("\n".join(sorted(seen)) + "\n")
