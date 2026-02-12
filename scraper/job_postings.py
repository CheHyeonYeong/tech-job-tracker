import requests
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict
import sys
import urllib.parse

sys.path.append(str(Path(__file__).parent))
from discord_notifier import send_discord_notification

DATA_FILE = Path(__file__).parent.parent / "data" / "jobs.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
}

# 관심 키워드
WANTED_KEYWORDS = ["백엔드", "프론트엔드", "신입", "주니어"]


def scrape_wanted_api(keyword: str = "", years: int = 0, limit: int = 20) -> List[Dict]:
    """원티드 API로 채용 공고 가져오기"""
    # years: -1 = 전체, 0 = 신입, 1 = 1년차 ...
    url = "https://www.wanted.co.kr/api/v4/jobs"
    params = {
        "country": "kr",
        "job_sort": "job.latest_order",
        "years": years,
        "locations": "all",
        "limit": limit,
    }

    if keyword:
        # 키워드 검색 API
        encoded = urllib.parse.quote(keyword)
        url = f"https://www.wanted.co.kr/api/v4/jobs?query={encoded}&country=kr&job_sort=job.latest_order&years={years}&limit={limit}"
        params = {}

    try:
        response = requests.get(url, params=params, headers=HEADERS, timeout=30)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"Failed to fetch wanted API: {e}")
        return []

    jobs = []
    for job in data.get("data", []):
        try:
            company_name = job.get("company", {}).get("name", "")
            position = job.get("position", "")
            job_id = job.get("id", "")

            jobs.append({
                "title": position,
                "company": company_name,
                "link": f"https://www.wanted.co.kr/wd/{job_id}",
                "source": "wanted.co.kr",
                "keyword": keyword or "신입",
                "scraped_at": datetime.now().isoformat()
            })
        except Exception as e:
            print(f"Error parsing wanted job: {e}")

    print(f"Scraped {len(jobs)} jobs from wanted.co.kr (keyword: {keyword or '신입'})")
    return jobs


def scrape_saramin_api(keyword: str = "신입 개발자", count: int = 20) -> List[Dict]:
    """사람인 검색 (HTML 파싱 - API 없음)"""
    encoded = urllib.parse.quote(keyword)
    url = f"https://www.saramin.co.kr/zf_user/search/recruit?searchType=search&searchword={encoded}&recruitPage=1&recruitSort=relation&recruitPageCount={count}"

    try:
        response = requests.get(url, headers={
            "User-Agent": HEADERS["User-Agent"],
            "Accept": "text/html",
        }, timeout=30)
        response.raise_for_status()
    except Exception as e:
        print(f"Failed to fetch saramin: {e}")
        return []

    from bs4 import BeautifulSoup
    soup = BeautifulSoup(response.text, 'lxml')
    jobs = []

    for item in soup.select('.item_recruit'):
        try:
            title_elem = item.select_one('.job_tit a')
            company_elem = item.select_one('.corp_name a')

            if not title_elem:
                continue

            title = title_elem.get_text(strip=True)
            company = company_elem.get_text(strip=True) if company_elem else ""
            link = title_elem.get('href', '')

            if link and not link.startswith('http'):
                link = f"https://www.saramin.co.kr{link}"

            jobs.append({
                "title": title,
                "company": company,
                "link": link,
                "source": "saramin.co.kr",
                "keyword": keyword,
                "scraped_at": datetime.now().isoformat()
            })
        except Exception as e:
            print(f"Error parsing saramin job: {e}")

    print(f"Scraped {len(jobs)} jobs from saramin.co.kr (keyword: {keyword})")
    return jobs


def scrape_jobkorea(keyword: str = "신입 개발자", count: int = 20) -> List[Dict]:
    """잡코리아 검색"""
    encoded = urllib.parse.quote(keyword)
    url = f"https://www.jobkorea.co.kr/Search/?stext={encoded}&tabType=recruit&Page_No=1"

    try:
        response = requests.get(url, headers={
            "User-Agent": HEADERS["User-Agent"],
            "Accept": "text/html",
        }, timeout=30)
        response.raise_for_status()
    except Exception as e:
        print(f"Failed to fetch jobkorea: {e}")
        return []

    from bs4 import BeautifulSoup
    soup = BeautifulSoup(response.text, 'lxml')
    jobs = []

    for item in soup.select('.list-item, .item'):
        try:
            title_elem = item.select_one('.title, .job-tit a, a.title')
            company_elem = item.select_one('.name, .corp-name a')

            if not title_elem:
                continue

            title = title_elem.get_text(strip=True)
            company = company_elem.get_text(strip=True) if company_elem else ""
            link = title_elem.get('href', '')

            if link and not link.startswith('http'):
                link = f"https://www.jobkorea.co.kr{link}"

            if title and link:
                jobs.append({
                    "title": title,
                    "company": company,
                    "link": link,
                    "source": "jobkorea.co.kr",
                    "keyword": keyword,
                    "scraped_at": datetime.now().isoformat()
                })
        except Exception as e:
            print(f"Error parsing jobkorea job: {e}")

    print(f"Scraped {len(jobs)} jobs from jobkorea.co.kr (keyword: {keyword})")
    return jobs


def scrape_jumpit(keyword: str = "", years: int = 0) -> List[Dict]:
    """점핏 API (신입 개발자 채용)"""
    url = "https://api.jumpit.co.kr/api/positions"
    params = {
        "sort": "reg_dt",
        "highlight": "false",
        "page": 1,
        "size": 20,
    }
    if years == 0:
        params["career"] = "0"  # 신입

    try:
        response = requests.get(url, params=params, headers=HEADERS, timeout=30)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"Failed to fetch jumpit: {e}")
        return []

    jobs = []
    for job in data.get("result", {}).get("positions", []):
        try:
            jobs.append({
                "title": job.get("title", ""),
                "company": job.get("companyName", ""),
                "link": f"https://www.jumpit.co.kr/position/{job.get('id', '')}",
                "source": "jumpit.co.kr",
                "keyword": "신입" if years == 0 else keyword,
                "scraped_at": datetime.now().isoformat()
            })
        except Exception as e:
            print(f"Error parsing jumpit job: {e}")

    print(f"Scraped {len(jobs)} jobs from jumpit.co.kr")
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

    # 1. 원티드 - 신입 (years=0)
    wanted_jobs = scrape_wanted_api(years=0, limit=30)
    all_current.extend(wanted_jobs)

    # 2. 원티드 - 키워드 검색
    for keyword in WANTED_KEYWORDS:
        jobs = scrape_wanted_api(keyword=keyword, years=-1, limit=15)
        all_current.extend(jobs)

    # 3. 점핏 - 신입
    jumpit_jobs = scrape_jumpit(years=0)
    all_current.extend(jumpit_jobs)

    # 4. 사람인
    saramin_jobs = scrape_saramin_api("신입 백엔드", 15)
    all_current.extend(saramin_jobs)
    saramin_jobs2 = scrape_saramin_api("신입 프론트엔드", 15)
    all_current.extend(saramin_jobs2)

    # 5. 잡코리아
    jobkorea_jobs = scrape_jobkorea("신입 개발자", 15)
    all_current.extend(jobkorea_jobs)

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
        for job in new_jobs[:10]:  # 처음 10개만 출력
            print(f"  - [{job.get('company', '?')}] {job['title'][:50]}")

        # Discord 알림
        formatted_jobs = [
            {
                'title': f"[{j.get('company', '?')}] {j['title'][:50]}",
                'link': j['link'],
                'description': f"{j['source']} | {j.get('keyword', '')}"
            }
            for j in new_jobs[:10]
        ]
        send_discord_notification(
            f"새 채용 공고 {len(new_jobs)}개",
            formatted_jobs,
            color=0x36B37E
        )
    else:
        print("\n새 채용 공고 없음")

    # 저장 (최신 500개 유지)
    all_jobs = unique_jobs + [j for j in previous if j['link'] not in {c['link'] for c in unique_jobs}]
    all_jobs = all_jobs[:500]
    save_jobs(all_jobs, DATA_FILE)
    print(f"Saved {len(all_jobs)} jobs")


if __name__ == "__main__":
    main()
