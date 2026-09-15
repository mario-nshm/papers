import feedparser
import requests
import json
import os
import re
import time
from datetime import datetime, timezone, timedelta

FEEDS = [
    "https://vnexpress.net/rss/kinh-doanh.rss",
    "https://cafef.vn/rss/trang-chu.rss",
    "https://vietstock.vn/rss/tai-chinh.rss",
]

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent?key={GEMINI_API_KEY}"

VN_TZ = timezone(timedelta(hours=7))

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}


def fetch_full_article(url):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        html = resp.text
        # Lấy nội dung bài từ các tag phổ biến
        # VnExpress: <article class="fck_detail">
        # CafeF: <div class="detail-content">
        # Vietstock: <div class="article-content">
        patterns = [
            r'<article[^>]*class="[^"]*fck_detail[^"]*"[^>]*>(.*?)</article>',
            r'<div[^>]*class="[^"]*detail-content[^"]*"[^>]*>(.*?)</div>\s*<div',
            r'<div[^>]*class="[^"]*article-content[^"]*"[^>]*>(.*?)</div>\s*<div',
            r'<div[^>]*class="[^"]*content-detail[^"]*"[^>]*>(.*?)</div>\s*<div',
            r'<div[^>]*id="[^"]*content[^"]*"[^>]*>(.*?)</div>',
        ]
        for pat in patterns:
            m = re.search(pat, html, re.DOTALL | re.IGNORECASE)
            if m:
                text = re.sub(r'<[^>]+>', ' ', m.group(1))
                text = re.sub(r'\s+', ' ', text).strip()
                if len(text) > 100:
                    return text[:3000]
        # Fallback: lấy tất cả <p> tags
        paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', html, re.DOTALL)
        text = ' '.join(re.sub(r'<[^>]+>', '', p).strip() for p in paragraphs)
        text = re.sub(r'\s+', ' ', text).strip()
        if len(text) > 100:
            return text[:3000]
    except Exception:
        pass
    return ""


def fetch_articles():
    articles = []
    for url in FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:10]:
                link = entry.get("link", "")
                print(f"  Crawl: {link}")
                full_text = fetch_full_article(link)
                time.sleep(0.5)
                articles.append({
                    "title": entry.get("title", ""),
                    "summary": entry.get("summary", ""),
                    "full_text": full_text,
                    "link": link,
                    "source": feed.feed.get("title", url),
                })
        except Exception:
            continue
    return articles


def summarize(articles):
    text = "\n\n".join(
        f"[{a['source']}] {a['title']}\n{a['full_text'] or a['summary']}"
        for a in articles
    )
    prompt = (
        "Bạn là chuyên gia tài chính Việt Nam. "
        "Dưới đây là NỘI DUNG ĐẦY ĐỦ các bài báo tài chính hôm nay. "
        "Hãy tổng hợp thành ĐÚNG 10 dòng bullet ngắn gọn, tiếng Việt, "
        "mỗi dòng 1 ý chính, ưu tiên: chứng khoán, tỷ giá, lãi suất, bất động sản, chính sách kinh tế. "
        "Không giải thích thêm.\n\n"
        f"{text}"
    )
    resp = requests.post(GEMINI_URL, json={
        "contents": [{"parts": [{"text": prompt}]}]
    })
    resp.raise_for_status()
    data = resp.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]


def build_html(summary):
    now = datetime.now(VN_TZ).strftime("%d/%m/%Y %H:%M")
    return f"""<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Tin Tài Chính VN</title>
<style>
  body {{ font-family: system-ui, sans-serif; max-width: 600px; margin: 40px auto; padding: 0 16px; background: #fafafa; color: #222; }}
  h1 {{ font-size: 1.2rem; font-weight: 600; }}
  .date {{ color: #888; font-size: 0.85rem; margin-bottom: 24px; }}
  .content {{ line-height: 1.7; white-space: pre-wrap; }}
</style>
</head>
<body>
<h1>Tin Tài Chính Việt Nam</h1>
<div class="date">Cập nhật: {now} (GMT+7)</div>
<div class="content">{summary}</div>
</body>
</html>"""


def main():
    articles = fetch_articles()
    if not articles:
        print("Không cào được tin nào.")
        return
    has_full = sum(1 for a in articles if a["full_text"])
    print(f"Cào được {len(articles)} tin ({has_full} có full text), đang tóm tắt...")
    summary = summarize(articles)
    html = build_html(summary)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("Đã ghi index.html")


if __name__ == "__main__":
    main()
