"""Lấy bài từ các kênh Telegram công khai (bản xem trước t.me/s/<kênh>) và gộp vào posts.json."""
import html, json, pathlib, re, sys, time, unicodedata, urllib.request

# since: chỉ giữ bài từ mốc này trở đi (2025-12-31T17:00 UTC = 00:00 ngày 1/1/2026 giờ Việt Nam)
SOURCES = [
    {"ch": "dobaocrypto", "author": None, "since": None},
    # Trade Coin Chiến Lược: chỉ giữ bài có chữ ký Đỗ Bảo, từ 1/1/2026
    {"ch": "TradeCoinChienLuoc", "author": "do bao", "since": "2025-12-31T17:00:00"},
]
INCLUDE_UNSIGNED = False  # True = giữ cả bài không có chữ ký người đăng (kênh tự đăng)
MAX_PAGES = 400           # giới hạn an toàn, mỗi trang ~20 bài
OUT = pathlib.Path(__file__).with_name("posts.json")


def get(url):
    for i in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            return urllib.request.urlopen(req, timeout=30).read().decode("utf-8")
        except Exception:
            if i == 3:
                raise
            time.sleep(5 * (i + 1))


def clean(s):
    s = re.sub(r"<br\s*/?>", "\n", s)
    return html.unescape(re.sub(r"<[^>]+>", "", s)).strip()


def norm(s):
    s = unicodedata.normalize("NFD", s.lower().replace("đ", "d"))
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def parse(page, ch):
    posts = []
    for blk in re.split(r'(?=<div class="tgme_widget_message_wrap)', page)[1:]:
        m = re.search(r'data-post="[^"/]+/(\d+)"', blk)
        if not m:
            continue
        t = re.search(r'class="tgme_widget_message_text js-message_text"[^>]*>(.*?)</div>', blk, re.S)
        r = re.search(r'class="tgme_widget_message_text js-message_reply_text"[^>]*>(.*?)</div>', blk, re.S)
        d = re.search(r'<time[^>]*datetime="([^"]+)"', blk)
        a = re.search(r'tgme_widget_message_from_author[^>]*>(.*?)</span>', blk, re.S)
        posts.append({"ch": ch, "id": int(m.group(1)), "date": d.group(1) if d else None,
                      "author": clean(a.group(1)) if a else "",
                      "text": clean(t.group(1)) if t else "",
                      "reply": clean(r.group(1)) if r else ""})
    return posts


def keep(p, src):
    if not p["text"] and not p["reply"]:
        return False
    if src["since"] and p["date"] and p["date"] < src["since"]:
        return False
    if not src["author"]:
        return True
    if not p["author"]:
        return INCLUDE_UNSIGNED
    return src["author"] in norm(p["author"])


def fetch_source(src, store, meta):
    """Quét từ bài mới nhất lùi dần; dừng khi tới mốc since hoặc bài đã quét ở lần trước."""
    url, seen = f"https://t.me/s/{src['ch']}", 0
    last = meta.get(src["ch"], 0)
    top = last
    for _ in range(MAX_PAGES):
        page = parse(get(url), src["ch"])
        if not page:
            break
        seen += len(page)
        top = max(top, max(p["id"] for p in page))
        for p in page:
            if keep(p, src):
                store[(p["ch"], p["id"])] = p
        lo = min(p["id"] for p in page)
        dates = [p["date"] for p in page if p["date"]]
        if lo <= last:
            break
        if src["since"] and dates and min(dates) < src["since"]:
            break
        url = f"https://t.me/s/{src['ch']}?before={lo}"
        time.sleep(0.7)
    meta[src["ch"]] = top
    return seen


def main():
    old = json.loads(OUT.read_text("utf-8")) if OUT.exists() else []
    store, meta = {}, {}
    for p in old:
        if p.get("ch") == "_meta":  # ghi nhớ bài mới nhất đã quét để lần sau chạy nhanh
            meta[p["src"]] = p["id"]
            continue
        p.setdefault("ch", "dobaocrypto")
        store[(p["ch"], p["id"])] = p
    total = 0
    for src in SOURCES:
        try:
            n = fetch_source(src, store, meta)
            print(f"{src['ch']}: đã quét {n} bài")
            total += n
        except Exception as e:
            print(f"{src['ch']}: lỗi {e}")
    if not total:
        sys.exit("Không đọc được bài nào: kiểm tra lại kênh hoặc cấu trúc trang.")
    since = {s["ch"]: s["since"] for s in SOURCES}
    rows = [p for k, p in sorted(store.items())
            if not (since.get(p["ch"]) and p["date"] and p["date"] < since[p["ch"]])]
    rows += [{"ch": "_meta", "src": c, "id": i, "date": None, "text": "", "reply": ""} for c, i in meta.items()]
    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=1), "utf-8")
    print(f"Đã lưu {len(rows) - len(meta)} bài.")


if __name__ == "__main__":
    main()
