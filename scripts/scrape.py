import os, sys, re, json, datetime, urllib.request

KEY = os.environ["FIRECRAWL_API_KEY"]
HOOK = os.environ.get("DRIVE_WEBHOOK_URL", "")
TOKEN = os.environ.get("DRIVE_TOKEN", "")
ONLY = os.environ.get("ONLY_MEDIA", "").strip()
CAP = int(os.environ.get("DAILY_CAP", "30"))      # batas kredit per run/hari
SCRAPE_PER_ACCOUNT = int(os.environ.get("SCRAPE_PER_ACCOUNT", "2"))
TODAY = datetime.date.today().isoformat()
used = 0

os.makedirs("data", exist_ok=True)
seen = set(open("data/seen.txt").read().split()) if os.path.exists("data/seen.txt") else set()


LIMIT = CAP  # batas efektif; dipersempit per akun agar semua akun kebagian


def fc(path, body, cost):
    """Panggil Firecrawl; berhenti bila batas kredit akan terlewati."""
    global used
    if used + cost > LIMIT:
        raise RuntimeError("CAP")
    used += cost
    req = urllib.request.Request(
        "https://api.firecrawl.dev/v1/" + path, data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def deliver(account, name, content):
    if HOOK:
        try:
            req = urllib.request.Request(HOOK, data=json.dumps(
                {"token": TOKEN, "media": account, "files": [{"name": name, "content": content}]}).encode(),
                headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=120) as r:
                if json.load(r).get("ok"):
                    print("  Drive OK")
                    return
        except Exception as e:
            print(f"  Drive GAGAL: {e}", file=sys.stderr)
    d = f"data/{account}"
    os.makedirs(d, exist_ok=True)
    open(f"{d}/{name}", "w").write(content)
    print(f"  Fallback: {d}/{name}")


cfg = json.load(open("sources.json"))
stop = False
for account, queries in cfg.items():
    if stop or (ONLY and ONLY != account):
        continue
    print(f"== {account}")
    n_acc = len(cfg) if not ONLY else 1
    LIMIT = min(CAP, used + CAP // n_acc)  # jatah akun ini
    items, urls = [], set()
    try:
        for q in queries[:2]:
            res = fc("search", {"query": q, "limit": 6, "lang": "id", "country": "id", "tbs": "qdr:d"}, 2).get("data", [])
            if not res:  # tidak ada hasil 24 jam -> longgarkan ke 1 minggu
                res = fc("search", {"query": q, "limit": 6, "lang": "id", "country": "id", "tbs": "qdr:w"}, 2).get("data", [])
            for r in res:
                if r["url"] not in urls:
                    urls.add(r["url"]); items.append(r)
        fresh = [r for r in items if r["url"] not in seen][:SCRAPE_PER_ACCOUNT]
        for r in fresh:
            md = fc("scrape", {"url": r["url"], "formats": ["markdown"], "onlyMainContent": True}, 1)["data"]["markdown"]
            r["excerpt"] = re.sub(r"\n{3,}", "\n\n", md)[:2500]
            seen.add(r["url"])
    except RuntimeError:
        print(f"  Jatah kredit akun ini habis (terpakai {used}/{CAP})", file=sys.stderr)
        if used >= CAP:
            stop = True
    except Exception as e:
        print(f"  GAGAL {account}: {e}", file=sys.stderr)
    if not items:
        continue
    out = [f"# {account} — bahan utas {TODAY}", f"Kredit terpakai sejauh ini: {used}/{CAP}. Filter: 24 jam terakhir (jika kosong, 7 hari).\n", "## Berita/fakta"]
    for r in items:
        out.append(f"- **{r.get('title','')}** — {r.get('description','')}\n  {r['url']}")
    out.append("\n## Isi artikel terpilih (untuk angka & kutipan)")
    for r in items:
        if r.get("excerpt"):
            out.append(f"\n### {r.get('title','')}\nSumber: {r['url']}\n\n{r['excerpt']}")
    deliver(account, f"{TODAY}_bahan-utas.md", "\n".join(out))

open("data/seen.txt", "w").write("\n".join(sorted(seen)) + "\n")
print(f"Total kredit terpakai (perkiraan): {used}/{CAP}")
