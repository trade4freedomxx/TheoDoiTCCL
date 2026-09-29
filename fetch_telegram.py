"""Lấy bài mới từ kênh Telegram công khai (bản xem trước t.me/s/<kênh>) và gộp vào posts.json."""
import html, json, pathlib, re, sys, urllib.request

CHANNEL = "dobaocrypto"
PAGES = 8  # mỗi trang ~20 bài
OUT = pathlib.Path(__file__).with_name("posts.json")


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=30).read().decode("utf-8")


def clean(s):
    s = re.sub(r"<br\s*/?>", "\n", s)
    return html.unescape(re.sub(r"<[^>]+>", "", s)).strip()


def parse(page):
    posts = []
    for blk in re.split(r'(?=<div class="tgme_widget_message_wrap)', page)[1:]:
        m = re.search(r'data-post="[^"/]+/(\d+)"', blk)
        if not m:
            continue
        t = re.search(r'class="tgme_widget_message_text js-message_text"[^>]*>(.*?)</div>', blk, re.S)
        r = re.search(r'class="tgme_widget_message_text js-message_reply_text"[^>]*>(.*?)</div>', blk, re.S)
        d = re.search(r'<time[^>]*datetime="([^"]+)"', blk)
        text = clean(t.group(1)) if t else ""
        reply = clean(r.group(1)) if r else ""
        if not text and not reply:
            continue
        posts.append({"id": int(m.group(1)), "date": d.group(1) if d else None,
                      "text": text, "reply": reply})
    return posts


def main():
    old = json.loads(OUT.read_text("utf-8")) if OUT.exists() else []
    by_id = {p["id"]: p for p in old}
    url = f"https://t.me/s/{CHANNEL}"
    got = 0
    for _ in range(PAGES):
        page = parse(get(url))
        if not page:
            break
        for p in page:
            by_id[p["id"]] = p
        got += len(page)
        url = f"https://t.me/s/{CHANNEL}?before={min(p['id'] for p in page)}"
    if not got:
        sys.exit("Không đọc được bài nào: kiểm tra lại kênh hoặc cấu trúc trang.")
    OUT.write_text(json.dumps(sorted(by_id.values(), key=lambda p: p["id"]),
                              ensure_ascii=False, indent=1), "utf-8")
    print(f"Đã lấy {got} bài, tổng {len(by_id)} bài.")


if __name__ == "__main__":
    main()
