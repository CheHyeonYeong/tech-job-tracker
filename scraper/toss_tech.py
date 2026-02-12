import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict
import sys

# 상대 import를 위한 경로 추가
sys.path.append(str(Path(__file__).parent))
from discord_notifier import send_discord_notification

DATA_FILE = Path(__file__).parent.parent / "data" / "toss_articles.json"


def scrape_toss_tech() -> List[Dict]:
    """토스 테크 블로그 스크래핑"""
    url = "https://toss.tech/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Failed to fetch toss.tech: {e}")
        return []

    soup = BeautifulSoup(response.text, 'lxml')
    articles = []

    # 토스 테크 블로그 구조에 맞게 선택자 조정 필요
    # 일반적인 article/a 태그 패턴으로 시도
    for article in soup.select('a[href*="/article/"]'):
        try:
            title_elem = article.select_one('h3, h2, [class*="title"]')
            title = title_elem.get_text(strip=True) if title_elem else article.get_text(strip=True)[:100]

            link = article.get('href', '')
            if link and not link.startswith('http'):
                link = f"https://toss.tech{link}"

            if not title or not link:
                continue

            articles.append({
                'title': title,
                'link': link,
                'source': 'toss.tech',
                'scraped_at': datetime.now().isoformat()
            })
        except Exception as e:
            print(f"Error parsing article: {e}")
            continue

    # 중복 제거
    seen = set()
    unique_articles = []
    for article in articles:
        if article['link'] not in seen:
            seen.add(article['link'])
            unique_articles.append(article)

    print(f"Scraped {len(unique_articles)} articles from toss.tech")
    return unique_articles


def load_articles(filepath: Path) -> List[Dict]:
    """저장된 이전 데이터 로드"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_articles(articles: List[Dict], filepath: Path):
    """데이터 저장"""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)


def get_new_articles(current: List[Dict], previous: List[Dict]) -> List[Dict]:
    """이전에 없던 새 글만 반환"""
    previous_links = {a['link'] for a in previous}
    return [a for a in current if a['link'] not in previous_links]


def main():
    print("=== Toss Tech Blog Scraper ===")
    print(f"Data file: {DATA_FILE}")

    # 이전 데이터 로드
    previous = load_articles(DATA_FILE)
    print(f"Previous articles: {len(previous)}")

    # 현재 데이터 스크래핑
    current = scrape_toss_tech()
    print(f"Current articles: {len(current)}")

    # 새 글 확인
    new_articles = get_new_articles(current, previous)

    if new_articles:
        print(f"\n새 글 {len(new_articles)}개 발견!")
        for article in new_articles:
            print(f"  - {article['title']}")
            print(f"    {article['link']}")

        # Discord 알림
        send_discord_notification(
            "토스 테크 블로그 새 글",
            new_articles,
            color=0x0064FF  # 토스 블루
        )
    else:
        print("\n새 글 없음")

    # 데이터 저장 (현재 + 이전 병합, 최신 100개 유지)
    all_articles = current + [a for a in previous if a['link'] not in {c['link'] for c in current}]
    all_articles = all_articles[:100]  # 최신 100개만 유지
    save_articles(all_articles, DATA_FILE)
    print(f"Saved {len(all_articles)} articles")


if __name__ == "__main__":
    main()
