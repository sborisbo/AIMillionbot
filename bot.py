import feedparser
import anthropic
import requests
import os
import json
import hashlib
from datetime import datetime, timedelta

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
POSTED_FILE = "posted_ids.json"

from feeds import RSS_FEEDS

def load_posted():
    try:
        with open(POSTED_FILE) as f:
            return set(json.load(f))
    except:
        return set()

def save_posted(ids):
    with open(POSTED_FILE, "w") as f:
        json.dump(list(ids), f)

def fetch_recent_articles(hours=8):
    articles = []
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    for url in RSS_FEEDS:
        feed = feedparser.parse(url)
        for entry in feed.entries[:5]:
            pub = entry.get("published_parsed")
            if pub:
                pub_dt = datetime(*pub[:6])
                if pub_dt < cutoff:
                    continue
            articles.append({
                "id": hashlib.md5(entry.link.encode()).hexdigest(),
                "title": entry.title,
                "summary": entry.get("summary", "")[:800],
                "link": entry.link,
            })
    return articles

def rewrite_with_claude(article):
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    prompt = f"""Ты — редактор Telegram-канала об ИИ и деньгах для русскоязычной аудитории.

Перепиши эту новость как короткий пост для Telegram (3-5 предложений):
- На русском языке
- Живо и интересно, без канцелярита
- Объясни почему это важно для денег / бизнеса / карьеры
- Добавь 2-3 релевантных эмодзи
- В конце добавь ссылку: {article['link']}
- НЕ добавляй заголовок отдельно — сразу начинай с сути

Заголовок оригинала: {article['title']}
Краткое содержание: {article['summary']}
"""
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text

def post_to_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    })

def main():
    posted = load_posted()
    articles = fetch_recent_articles(hours=8)
    new_articles = [a for a in articles if a["id"] not in posted]

    for article in new_articles[:2]:
        print(f"Posting: {article['title']}")
        text = rewrite_with_claude(article)
        post_to_telegram(text)
        posted.add(article["id"])

    save_posted(posted)

if __name__ == "__main__":
    main()
