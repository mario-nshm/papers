import feedparser
import requests
import json
import os
from datetime import datetime, timezone, timedelta

FEEDS = [
    "https://vnexpress.net/rss/kinh-doanh.rss",
    "https://cafef.vn/rss/trang-chu.rss",
    "https://vietstock.vn/rss/tai-chinh.rss",
]

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"

VN_TZ = timezone(timedelta(hours=7))

def fetch_articles():
    articles = []
    for url in FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:15]:
                articles.append({
                    "title": entry.get("title", ""),
                    "summary": entry.get("summary", "")[:200],
                    "link": entry.get("link", ""),
                    "source": feed.feed.get("title", url),
                })
        except Exception:
            continue
    return articles

def summarize(articles):
    text = "\n".join(
        f"- [{a['source']}] {a['title']}: {a['summary']}"
        for a in articles
    )
    prompt = (
        "Bạn là chuyên gia tài chính Việt Nam. "
        "Dưới đây là danh sách tin tài chính hôm nay. "
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
    print(f"Cào được {len(articles)} tin, đang tóm tắt...")
    summary = summarize(articles)
    html = build_html(summary)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("Đã ghi index.html")

if __name__ == "__main__":
    main()
