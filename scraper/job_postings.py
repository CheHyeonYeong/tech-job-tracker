import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict
import sys
import re

sys.path.append(str(Path(__file__).parent))
from discord_notifier import send_discord_notification

DATA_FILE = Path(__file__).parent.parent / "data" / "jobs.json"

# 관심 키워드 설정
WANTED_KEYWORDS = [
    "백엔드",
    "프론트엔드",
    "신입",
]

WANTED_COMPANIES = [
    "토스",
    "카카오",
    "네이버",
    "라인",
    "쿠팡",
    "배달의민족",
    "당근",
]


def scrape_toss_careers() -> List[Dict]:
    """토스 채용 페이지 스크래핑"""
    url = "https://toss.im/career/jobs"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Failed to fetch toss careers: {e}")
        return []

    soup = BeautifulSoup(response.text, 'lxml')
    jobs = []

    # 토스 채용 페이지 구조에 맞게 파싱
    # React 앱이라 실제로는 API 호출이 필요할 수 있음
    for job_elem in soup.select('a[href*="/career/job-detail"]'):
        try:
            title = job_elem.get_text(strip=True)
            link = job_elem.get('href', '')
            if not link.startswith('http'):
                link = f"https://toss.im{link}"

            if title and link:
                jobs.append({
                    'title': title,
                    'link': link,
                    'company': '토스',
                    'source': 'toss.im',
                    'scraped_at': datetime.now().isoformat()
                })
        except Exception as e:
            print(f"Error parsing toss job: {e}")

    print(f"Scraped {len(jobs)} jobs from toss.im")
    return jobs


def scrape_wanted_search(keyword: str) -> List[Dict]:
    """원티드에서 키워드 검색"""
    url = f"https://www.wanted.co.kr/search?query={keyword}&tab=position"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Failed to fetch wanted.co.kr: {e}")
        return []

    soup = BeautifulSoup(response.text, 'lxml')
    jobs = []

    # 원티드도 React 앱이라 실제로는 API 호출 필요
    for job_card in soup.select('[class*="JobCard"], [class*="job-card"]'):
        try:
            title_elem = job_card.select_one('[class*="title"], h3, h4')
            company_elem = job_card.select_one('[class*="company"], [class*="name"]')
            link_elem = job_card.select_one('a[href*="/wd/"]')

            title = title_elem.get_text(strip=True) if title_elem else ""
            company = company_elem.get_text(strip=True) if company_elem else ""
            link = link_elem.get('href', '') if link_elem else ""

            if link and not link.startswith('http'):
                link = f"https://www.wanted.co.kr{link}"

            if title and link:
                jobs.append({
                    'title': title,
                    'company': company,
                    'link': link,
                    'keyword': keyword,
                    'source': 'wanted.co.kr',
                    'scraped_at': datetime.now().isoformat()
                })
        except Exception as e:
            print(f"Error parsing wanted job: {e}")

    print(f"Scraped {len(jobs)} jobs from wanted.co.kr (keyword: {keyword})")
    return jobs


def load_jobs(filepath: Path) -> List[Dict]:
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_jobs(jobs: List[Dict], filepath: Path):
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(jobs, f, ensure_ascii=False, indent=2)


def get_new_jobs(current: List[Dict], previous: List[Dict]) -> List[Dict]:
    previous_links = {j['link'] for j in previous}
    return [j for j in current if j['link'] not in previous_links]


def main():
    print("=== Job Postings Scraper ===")
    print(f"Data file: {DATA_FILE}")

    previous = load_jobs(DATA_FILE)
    print(f"Previous jobs: {len(previous)}")

    all_current = []

    # 토스 채용 스크래핑
    toss_jobs = scrape_toss_careers()
    all_current.extend(toss_jobs)

    # 원티드 키워드 검색
    for keyword in WANTED_KEYWORDS:
        wanted_jobs = scrape_wanted_search(keyword)
        all_current.extend(wanted_jobs)

    # 중복 제거
    seen = set()
    unique_jobs = []
    for job in all_current:
        if job['link'] not in seen:
            seen.add(job['link'])
            unique_jobs.append(job)

    print(f"\nTotal unique jobs: {len(unique_jobs)}")

    # 새 공고 확인
    new_jobs = get_new_jobs(unique_jobs, previous)

    if new_jobs:
        print(f"\n새 채용 공고 {len(new_jobs)}개 발견!")
        for job in new_jobs:
            company = job.get('company', '')
            print(f"  - [{company}] {job['title']}")

        # Discord 알림
        formatted_jobs = [
            {
                'title': f"[{j.get('company', '?')}] {j['title']}",
                'link': j['link'],
                'description': f"Source: {j['source']}"
            }
            for j in new_jobs
        ]
        send_discord_notification(
            "새 채용 공고",
            formatted_jobs,
            color=0x36B37E  # 그린
        )
    else:
        print("\n새 채용 공고 없음")

    # 저장 (최신 200개 유지)
    all_jobs = unique_jobs + [j for j in previous if j['link'] not in {c['link'] for c in unique_jobs}]
    all_jobs = all_jobs[:200]
    save_jobs(all_jobs, DATA_FILE)
    print(f"Saved {len(all_jobs)} jobs")


if __name__ == "__main__":
    main()
