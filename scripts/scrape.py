import os, sys, re, json, datetime, urllib.request, urllib.error

KEY = os.environ["FIRECRAWL_API_KEY"]
HOOK = os.environ.get("DRIVE_WEBHOOK_URL", "")
TOKEN = os.environ.get("DRIVE_TOKEN", "")
ONLY = os.environ.get("ONLY_MEDIA", "").strip()
CAP = int(os.environ.get("DAILY_CAP", "30"))      # batas kredit per run/hari
SCRAPE_PER_ACCOUNT = int(os.environ.get("SCRAPE_PER_ACCOUNT", "2"))
TODAY = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=7))).date().isoformat()  # tanggal WIB
used = 0

os.makedirs("data", exist_ok=True)
seen = set(open("data/seen.txt").read().split()) if os.path.exists("data/seen.txt") else set()


SOCIAL = re.compile(r"(facebook|instagram|tiktok|threads|twitter|x)\.(com|net)/", re.I)
BAD = re.compile(r"script\.google\.com|\b(seks|sex|porn|judi|slot|togel|casino)\b", re.I)
LIMIT = CAP  # batas efektif; dipersempit per akun agar semua akun kebagian


def fc(path, body, cost):
    """Panggil Firecrawl; berhenti bila batas kredit akan terlewati."""
    global used
    if used + cost > LIMIT:
        raise RuntimeError("CAP")
    req = urllib.request.Request(
        "https://api.firecrawl.dev/v1/" + path, data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json", "User-Agent": "Mozilla/5.0 (compatible; assistant-work)"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            out = json.load(r)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Firecrawl {path} HTTP {e.code}: {e.read()[:300].decode('utf-8','replace')}")
    used += cost  # dihitung hanya bila sukses
    return out


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
        except urllib.error.HTTPError as e:
            print(f"  Drive GAGAL HTTP {e.code}: {e.read()[:300].decode('utf-8','replace')}", file=sys.stderr)
        except Exception as e:
            print(f"  Drive GAGAL: {e}", file=sys.stderr)
    d = f"data/{account}"
    os.makedirs(d, exist_ok=True)
    open(f"{d}/{name}", "w").write(content)
    print(f"  Fallback: {d}/{name}")


if os.environ.get("CHECK_DRIVE") == "true":  # uji koneksi Drive saja, 0 kredit Firecrawl
    import hashlib
    h = lambda t: hashlib.sha256(t.encode()).hexdigest()[:10]
    expected = "https://script.google.com/macros/s/AKfycbwuR3ec9QpCXcjIYYFmgYOqwFr1vtD3VVjc4lfi-oW5p8JUM56gT3Si5FB_PywVOfx7/exec"
    print(f"Secret URL: panjang={len(HOOK)} hash={h(HOOK)} | URL dari user: hash={h(expected)} -> {'SAMA' if HOOK == expected else 'BEDA'}")
    print(f"Berakhiran /exec: {HOOK.endswith('/exec')}; token terisi: {bool(TOKEN)}")
    deliver("Spek Dulu", "_tes-koneksi.md", "Tes koneksi GitHub -> Drive berhasil.")
    sys.exit(0)

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
                if BAD.search(r["url"] + " " + r.get("title", "") + " " + r.get("description", "")):
                    continue  # buang spam/konten dewasa/judi
                if r["url"] not in urls:
                    urls.add(r["url"]); items.append(r)
        got = tries = 0
        for r in items:
            if got >= SCRAPE_PER_ACCOUNT or tries >= SCRAPE_PER_ACCOUNT + 3:
                break
            if r["url"] in seen or SOCIAL.search(r["url"]):
                continue  # situs sosial ditolak Firecrawl; cukup pakai ringkasan pencarian
            tries += 1
            try:  # situs yang ditolak Firecrawl (403) dilewati, coba kandidat berikutnya
                md = fc("scrape", {"url": r["url"], "formats": ["markdown"], "onlyMainContent": True}, 1)["data"]["markdown"]
            except RuntimeError as e:
                if str(e) == "CAP":
                    raise
                print(f"  lewati {r['url']}: {str(e)[:90]}", file=sys.stderr)
                continue
            r["excerpt"] = re.sub(r"\n{3,}", "\n\n", md)[:2500]
            seen.add(r["url"])
            got += 1
    except RuntimeError as e:
        print(f"  {e} (terpakai {used}/{CAP})", file=sys.stderr)
        if str(e) == "CAP" and used >= CAP:
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
