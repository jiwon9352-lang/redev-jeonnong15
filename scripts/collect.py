#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
전농15 대시보드 데이터 수집기
- 정비사업 정보몽땅(전농15 조합) '공지사항' 게시판을 긁어 data.json 을 생성한다.
- 자동 수집이 어려운(자바스크립트 렌더링) 결재문서/경과는 정적 항목으로 유지한다.
- GitHub Actions(update.yml)가 매일 1회 이 스크립트를 실행하고 data.json 변경분을 커밋한다.
저장 위치(리포지토리): scripts/collect.py   / 출력: 리포지토리 루트의 data.json
"""
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

CAFE_ID = "230900001492G47"                     # 정비몽땅 전농15 조합 카페 ID
BASE = "https://cleanup.seoul.go.kr"
BOARD_URL = f"{BASE}/assc/bbs-use/execute.do?cafeId={CAFE_ID}&bbsSn=13465&streSttusCode=0"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; jeonnong15-dashboard/1.0; +https://github.com/)"}
DATE_RE = re.compile(r"20\d{2}[-.]\d{1,2}[-.]\d{1,2}")

# --- 자동수집이 어려운 항목(결재문서 등)은 여기서 관리(가끔 손으로만 갱신) ---
STATIC_NOTICES = [
    {
        "cat": "결재", "date": "2026-06-11",
        "title": "전농제15구역 주택정비형 재개발사업 관련 결재문서",
        "by": "서울정보소통광장 · 결재문서", "real": True,
        "url": "https://opengov.seoul.go.kr/sanction/35366672",
    },
    {
        "cat": "결재", "date": "2026-05-27",
        "title": "전농제15구역 정비계획 수립 관련 검토 (결재)",
        "by": "서울정보소통광장 · 결재문서 검색",
        "url": "https://opengov.seoul.go.kr/sanction?search=%EC%A0%84%EB%86%8D%EC%A0%9C15%EA%B5%AC%EC%97%AD",
    },
    {
        "cat": "경과", "date": "",
        "title": "전농15구역 추진경과·사업개요 (정비몽땅 원문)",
        "by": "정비몽땅 조합 카페", "real": True,
        "url": f"{BASE}/cafe/mainIndx.do?cafeUrl=wjsshd15",
    },
]

# 스크래핑이 완전히 실패했을 때 최소한 보장할 공지(가장 최근 확인분)
FALLBACK_NOTICE = {
    "cat": "공지", "date": "2026-06-04",
    "title": "재개발사업 조합설립추진위원회 구성을 위한 주민설명회 개최 알림(전농동 152-65번지 일대)",
    "by": "정비몽땅 · 구청(공공지원자) 공지", "real": True,
    "url": f"{BASE}/assc/bbs-use/vscrGnrl.do?cafeId={CAFE_ID}&bbsSn=13465&nttSn=176124&menuId=100",
}


def scrape_board():
    """정비몽땅 공지 게시판에서 (제목, 날짜, 원문URL) 목록을 추출."""
    resp = requests.get(BOARD_URL, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    notices = []
    seen = set()
    for a in soup.select('a[href*="vscrGnrl.do"]'):   # 각 글의 상세 링크
        title = a.get_text(strip=True)
        href = a.get("href", "")
        if not title or not href or href in seen:
            continue
        seen.add(href)
        url = urljoin(BASE, href)
        date = ""
        row = a.find_parent("tr")
        if row:
            m = DATE_RE.search(row.get_text(" ", strip=True))
            if m:
                date = m.group(0).replace(".", "-")
        notices.append({
            "cat": "공지", "title": title, "date": date,
            "by": "정비몽땅 · 조합 공지", "real": True, "url": url,
        })
    return notices


def main():
    try:
        notices = scrape_board()
        print(f"scraped {len(notices)} 공지", file=sys.stderr)
    except Exception as e:
        print(f"scrape failed: {e}", file=sys.stderr)
        notices = []

    if not notices:                      # 실패/빈 결과면 최소 보장
        notices = [FALLBACK_NOTICE]

    all_notices = notices + STATIC_NOTICES

    kst = timezone(timedelta(hours=9))
    data = {
        "updatedAt": datetime.now(kst).strftime("%Y-%m-%d %H:%M KST"),
        "notices": all_notices,
    }
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"wrote data.json ({len(all_notices)} notices)")


if __name__ == "__main__":
    main()
