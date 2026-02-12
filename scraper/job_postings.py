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

# Java/Spring 백엔드 신입~1년차 키워드
SEARCH_KEYWORDS = [
    "java 백엔드",
    "spring 백엔드",
    "java 신입",
    "spring boot",
    "자바 백엔드",
    "백엔드 신입",
]


def scrape_wanted_api(keyword: str = "", years: int = 0, limit: int = 20) -> List[Dict]:
    """원티드 API - Java/Spring 백엔드"""
    if keyword:
        encoded = urllib.parse.quote(keyword)
        url = f"https://www.wanted.co.kr/api/v4/jobs?query={encoded}&country=kr&job_sort=job.latest_order&years={years}&limit={limit}"
    else:
        # 신입 백엔드 (tag_type_id=518 = 서버/백엔드)
        url = f"https://www.wanted.co.kr/api/v4/jobs?country=kr&tag_type_ids=518&job_sort=job.latest_order&years={years}&limit={limit}"

    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
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

            # Java/Spring 관련 공고만 필터링 (키워드 검색이 아닌 경우)
            if not keyword:
                pos_lower = position.lower()
                if not any(kw in pos_lower for kw in ['java', 'spring', '자바', '스프링', '백엔드', 'backend']):
                    continue

            jobs.append({
                "title": position,
                "company": company_name,
                "link": f"https://www.wanted.co.kr/wd/{job_id}",
                "source": "wanted",
                "keyword": keyword or "백엔드",
                "scraped_at": datetime.now().isoformat()
            })
        except Exception as e:
            print(f"Error parsing wanted job: {e}")

    print(f"Scraped {len(jobs)} jobs from wanted (keyword: {keyword or '백엔드 신입'})")
    return jobs


def scrape_jumpit_api(career: str = "1") -> List[Dict]:
    """점핏 API - 백엔드/서버 신입~1년차
    career: 1 = 신입(0-1년)
    """
    url = "https://api.jumpit.co.kr/api/positions"
    params = {
        "sort": "reg_dt",
        "highlight": "false",
        "page": 1,
        "size": 30,
        "jobCategory": "1",  # 1 = 서버/백엔드
        "career": career,
    }

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
            title = job.get("title", "")
            # Java/Spring 관련만 필터링
            title_lower = title.lower()
            tech_stacks = [t.lower() for t in job.get("techStacks", [])]
            all_text = title_lower + " " + " ".join(tech_stacks)

            if not any(kw in all_text for kw in ['java', 'spring', '자바', '스프링']):
                continue

            jobs.append({
                "title": title,
                "company": job.get("companyName", ""),
                "link": f"https://www.jumpit.co.kr/position/{job.get('id', '')}",
                "source": "jumpit",
                "keyword": "Java/Spring 백엔드",
                "scraped_at": datetime.now().isoformat()
            })
        except Exception as e:
            print(f"Error parsing jumpit job: {e}")

    print(f"Scraped {len(jobs)} jobs from jumpit (Java/Spring 백엔드)")
    return jobs


def scrape_saramin(keyword: str, count: int = 20) -> List[Dict]:
    """사람인 검색 - Java/Spring 백엔드"""
    from bs4 import BeautifulSoup

    encoded = urllib.parse.quote(keyword)
    url = f"https://www.saramin.co.kr/zf_user/search/recruit?searchType=search&searchword={encoded}&recruitPage=1&recruitSort=relation&recruitPageCount={count}&exp_cd=1"  # exp_cd=1: 신입

    try:
        response = requests.get(url, headers={
            "User-Agent": HEADERS["User-Agent"],
            "Accept": "text/html",
        }, timeout=30)
        response.raise_for_status()
    except Exception as e:
        print(f"Failed to fetch saramin: {e}")
        return []

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
                "source": "saramin",
                "keyword": keyword,
                "scraped_at": datetime.now().isoformat()
            })
        except Exception as e:
            print(f"Error parsing saramin job: {e}")

    print(f"Scraped {len(jobs)} jobs from saramin (keyword: {keyword})")
    return jobs


def scrape_zighang() -> List[Dict]:
    """직행 - Java/Spring 백엔드 신입
    Note: 직행은 CSR이라 HTML에서 데이터 추출이 어려움
    API 발견 시 업데이트 필요
    """
    # 직행 API 시도
    url = "https://zighang.com/api/recruitment"
    params = {
        "career": "NEWCOMER",
        "position": "BACKEND",
    }

    try:
        response = requests.get(url, params=params, headers=HEADERS, timeout=30)
        if response.status_code == 200:
            data = response.json()
            jobs = []
            for job in data.get("data", data.get("recruitments", [])):
                jobs.append({
                    "title": job.get("title", ""),
                    "company": job.get("companyName", job.get("company", {}).get("name", "")),
                    "link": f"https://zighang.com/recruitment/{job.get('id', '')}",
                    "source": "zighang",
                    "keyword": "백엔드 신입",
                    "scraped_at": datetime.now().isoformat()
                })
            print(f"Scraped {len(jobs)} jobs from zighang")
            return jobs
    except Exception as e:
        print(f"Zighang API not available: {e}")

    print("Scraped 0 jobs from zighang (CSR site - API not found)")
    return []


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
    print("=== Job Postings Scraper (Java/Spring Backend 신입~1년차) ===")
    print(f"Data file: {DATA_FILE}")

    previous = load_jobs(DATA_FILE)
    print(f"Previous jobs: {len(previous)}")

    all_current = []

    # 1. 원티드 - 백엔드 신입 (years=0~1)
    for years in [0, 1]:
        jobs = scrape_wanted_api(years=years, limit=30)
        all_current.extend(jobs)

    # 2. 원티드 - Java/Spring 키워드 검색
    for keyword in ["java 백엔드 신입", "spring boot 신입", "자바 개발자 신입"]:
        jobs = scrape_wanted_api(keyword=keyword, years=1, limit=20)
        all_current.extend(jobs)

    # 3. 점핏 - 백엔드 신입
    jumpit_jobs = scrape_jumpit_api(career="1")
    all_current.extend(jumpit_jobs)

    # 4. 사람인 - Java/Spring 신입
    for keyword in ["java 신입", "spring boot 신입", "자바 백엔드 신입"]:
        saramin_jobs = scrape_saramin(keyword, 15)
        all_current.extend(saramin_jobs)

    # 5. 직행 (CSR이라 API 필요)
    zighang_jobs = scrape_zighang()
    all_current.extend(zighang_jobs)

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
        for job in new_jobs[:10]:
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
            f"Java/Spring 백엔드 신입 공고 {len(new_jobs)}개",
            formatted_jobs,
            color=0x36B37E
        )
    else:
        print("\n새 채용 공고 없음")

    # 저장 (최신 300개 유지)
    all_jobs = unique_jobs + [j for j in previous if j['link'] not in {c['link'] for c in unique_jobs}]
    all_jobs = all_jobs[:300]
    save_jobs(all_jobs, DATA_FILE)
    print(f"Saved {len(all_jobs)} jobs")


if __name__ == "__main__":
    main()
