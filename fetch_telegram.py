"""Lấy bài từ các kênh Telegram công khai (bản xem trước t.me/s/<kênh>) và gộp vào posts.json."""
import html, json, pathlib, re, sys, time, unicodedata, urllib.request

SOURCES = [
    {"ch": "dobaocrypto", "pages": 8, "author": None},
    # Chỉ giữ bài có chữ ký người đăng là Đỗ Bảo
    {"ch": "TradeCoinChienLuoc", "pages": 30, "author": "do bao"},
]
INCLUDE_UNSIGNED = False  # True = giữ cả bài không có chữ ký người đăng (kênh tự đăng)
OUT = pathlib.Path(__file__).with_name("posts.json")


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=30).read().decode("utf-8")


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
        text = clean(t.group(1)) if t else ""
        reply = clean(r.group(1)) if r else ""
        if not text and not reply:
            continue
        posts.append({"ch": ch, "id": int(m.group(1)), "date": d.group(1) if d else None,
                      "author": clean(a.group(1)) if a else "", "text": text, "reply": reply})
    return posts


def keep(p, author):
    if not author:
        return True
    if not p["author"]:
        return INCLUDE_UNSIGNED
    return author in norm(p["author"])


def fetch_source(src, store):
    url, seen = f"https://t.me/s/{src['ch']}", 0
    for _ in range(src["pages"]):
        page = parse(get(url), src["ch"])
        if not page:
            break
        seen += len(page)
        for p in page:
            if keep(p, src["author"]):
                store[(p["ch"], p["id"])] = p
        url = f"https://t.me/s/{src['ch']}?before={min(p['id'] for p in page)}"
        time.sleep(0.5)
    return seen


def main():
    old = json.loads(OUT.read_text("utf-8")) if OUT.exists() else []
    store = {}
    for p in old:
        p.setdefault("ch", "dobaocrypto")
        store[(p["ch"], p["id"])] = p
    total = 0
    for src in SOURCES:
        try:
            n = fetch_source(src, store)
            print(f"{src['ch']}: đọc {n} bài")
            total += n
        except Exception as e:
            print(f"{src['ch']}: lỗi {e}")
    if not total:
        sys.exit("Không đọc được bài nào: kiểm tra lại kênh hoặc cấu trúc trang.")
    OUT.write_text(json.dumps([store[k] for k in sorted(store)], ensure_ascii=False, indent=1), "utf-8")
    print(f"Tổng {len(store)} bài đã lưu.")


if __name__ == "__main__":
    main()
