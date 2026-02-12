import requests
import os
from typing import List, Dict

DISCORD_WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK_URL')


def send_discord_notification(title: str, articles: List[Dict], color: int = 0x0064FF):
    """Discord Webhook으로 새 글 알림 전송"""
    if not DISCORD_WEBHOOK_URL:
        print("DISCORD_WEBHOOK_URL not set, skipping notification")
        return False

    if not articles:
        print("No articles to notify")
        return False

    embeds = []
    for article in articles[:10]:  # Discord 제한: embed 10개까지
        embed = {
            "title": article.get('title', 'No title'),
            "url": article.get('link', ''),
            "color": color,
        }
        if article.get('date'):
            embed["footer"] = {"text": article['date']}
        if article.get('description'):
            embed["description"] = article['description'][:200]
        embeds.append(embed)

    payload = {
        "content": f"**{title}** - 새 글 {len(articles)}개!",
        "embeds": embeds
    }

    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
        response.raise_for_status()
        print(f"Discord notification sent: {response.status_code}")
        return True
    except requests.RequestException as e:
        print(f"Failed to send Discord notification: {e}")
        return False


if __name__ == "__main__":
    # 테스트
    test_articles = [
        {
            "title": "테스트 글",
            "link": "https://toss.tech/test",
            "date": "2026-02-12",
            "description": "테스트 설명입니다."
        }
    ]
    send_discord_notification("테스트 알림", test_articles)
