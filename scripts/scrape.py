#!/usr/bin/env python3
"""Scrape Korean hot-deal communities and write data/deals.json."""

import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

MAX_PER_SITE = 30
NOW = datetime.now(timezone.utc).isoformat()

NOTICE_KEYWORDS = ["공지", "알림", "이용 규칙", "비밀번호"]


def get_html(url: str, extra_headers=None) -> requests.Response:
    headers = {**HEADERS, **(extra_headers or {})}
    return requests.get(url, headers=headers, timeout=15)


def parse_int(text: str) -> int:
    """Parse integer from text, stripping commas and whitespace."""
    try:
        cleaned = re.sub(r"[^\d]", "", text.strip())
        return int(cleaned) if cleaned else 0
    except (ValueError, AttributeError):
        return 0


# ── 뽐뿌 핫딜 ────────────────────────────────────────────────────────────────

def scrape_ppomppu() -> list[dict]:
    posts = []
    try:
        url = "https://www.ppomppu.co.kr/zboard/zboard.php?id=ppomppu"
        res = get_html(url, {"Referer": "https://www.ppomppu.co.kr/"})
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "lxml")

        for tr in soup.select("tr.baseList"):
            a = tr.select_one("a.baseList-title")
            if not a:
                continue

            # Title: grab the span text (may have em.baseList-head prefix)
            span = a.select_one("span")
            if span:
                # Remove category prefix em
                for em in span.select("em.baseList-head"):
                    em.decompose()
                title = span.get_text(strip=True)
            else:
                title = a.get_text(strip=True)

            if not title or len(title) < 3:
                continue
            if any(k in title for k in NOTICE_KEYWORDS):
                continue

            href = a.get("href", "")
            if "no=" not in href:
                continue
            if href.startswith("http"):
                full_url = href
            else:
                full_url = "https://www.ppomppu.co.kr/zboard/" + href.lstrip("/")

            # Thumb
            thumb = None
            thumb_a = tr.select_one("a.baseList-thumb img")
            if thumb_a:
                src = thumb_a.get("src", "")
                if src:
                    thumb = ("https:" + src) if src.startswith("//") else src

            # Score: "25 - 0" format → take first number
            score = 0
            rec_td = tr.select_one("td.baseList-rec")
            if rec_td:
                rec_text = rec_td.get_text(strip=True)
                m = re.search(r"(\d+)", rec_text)
                if m:
                    score = int(m.group(1))

            # Views
            views = None
            hit_td = tr.select_one("td.baseList-views")
            if hit_td:
                views = parse_int(hit_td.get_text())

            post_id = re.search(r"no=(\d+)", full_url)
            posts.append({
                "id":         post_id.group(1) if post_id else full_url,
                "site":       "ppomppu",
                "title":      title,
                "url":        full_url,
                "thumb":      thumb,
                "score":      score,
                "views":      views,
                "crawled_at": NOW,
            })
            if len(posts) >= MAX_PER_SITE:
                break

        print(f"[ppomppu] {len(posts)} posts")
    except Exception as e:
        print(f"[ppomppu] FAILED: {e}", file=sys.stderr)
    return posts


# ── 클리앙 알뜰구매 ───────────────────────────────────────────────────────────

def scrape_clien() -> list[dict]:
    posts = []
    try:
        url = "https://www.clien.net/service/board/jirum"
        res = get_html(url, {"Referer": "https://www.clien.net/"})
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "lxml")

        # Real deal rows have class 'jirum' or 'sold_out' (not notice)
        for div in soup.select("div.list_item.jirum, div.list_item.sold_out"):
            a = div.select_one("span.list_subject a") or div.select_one("a.list_subject")
            if not a:
                continue

            title = a.get_text(strip=True)
            if not title or len(title) < 3:
                continue
            if any(k in title for k in NOTICE_KEYWORDS):
                continue

            href = a.get("href", "")
            if not href:
                continue
            full_url = ("https://www.clien.net" + href) if href.startswith("/") else href

            # Thumb
            thumb = None
            img = div.select_one("div.list_image img")
            if img:
                src = img.get("src", "")
                if src and "noimage" not in src:
                    thumb = src

            # Views: span.hit
            views = None
            hit_el = div.select_one("div.list_hit span.hit")
            if hit_el:
                views_text = hit_el.get_text(strip=True).replace("k", "000").replace("K", "000")
                views = parse_int(views_text)

            # Timestamp
            ts_el = div.select_one("span.timestamp")
            ts = ts_el.get_text(strip=True) if ts_el else None

            post_id = re.search(r"/(\d+)$", href)
            posts.append({
                "id":         post_id.group(1) if post_id else href,
                "site":       "clien",
                "title":      title,
                "url":        full_url,
                "thumb":      thumb,
                "score":      views or 0,   # clien has no recommend; use views
                "views":      views,
                "crawled_at": NOW,
            })
            if len(posts) >= MAX_PER_SITE:
                break

        print(f"[clien] {len(posts)} posts")
    except Exception as e:
        print(f"[clien] FAILED: {e}", file=sys.stderr)
    return posts


# ── 루리웹 핫딜 ───────────────────────────────────────────────────────────────

def scrape_ruliweb() -> list[dict]:
    posts = []
    try:
        url = "https://bbs.ruliweb.com/market/board/1020"
        res = get_html(url, {"Referer": "https://bbs.ruliweb.com/"})
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "lxml")

        for tr in soup.select("tr.table_body"):
            # Skip notices
            if "notice" in tr.get("class", []):
                continue

            a = tr.select_one("a.subject_link.deco") or tr.select_one("a.deco")
            if not a:
                continue

            title = a.get_text(strip=True)
            if not title or len(title) < 3:
                continue
            if any(k in title for k in NOTICE_KEYWORDS):
                continue

            href = a.get("href", "")
            if not href:
                continue
            full_url = href if href.startswith("http") else "https://bbs.ruliweb.com" + href

            # Score
            score = 0
            rec_td = tr.select_one("td.recomd")
            if rec_td:
                score = parse_int(rec_td.get_text())

            # Views
            views = None
            hit_td = tr.select_one("td.hit")
            if hit_td:
                views = parse_int(hit_td.get_text())

            post_id = re.search(r"/(\d+)", href)
            posts.append({
                "id":         post_id.group(1) if post_id else href,
                "site":       "ruliweb",
                "title":      title,
                "url":        full_url,
                "thumb":      None,
                "score":      score,
                "views":      views,
                "crawled_at": NOW,
            })
            if len(posts) >= MAX_PER_SITE:
                break

        print(f"[ruliweb] {len(posts)} posts")
    except Exception as e:
        print(f"[ruliweb] FAILED: {e}", file=sys.stderr)
    return posts


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    out_path = Path(__file__).parent.parent / "data" / "deals.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    all_posts: list[dict] = []

    for scraper in [scrape_ppomppu, scrape_clien, scrape_ruliweb]:
        all_posts.extend(scraper())
        time.sleep(1)

    all_posts.sort(key=lambda p: p.get("score", 0), reverse=True)

    out_path.write_text(json.dumps(all_posts, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✅ Saved {len(all_posts)} posts to {out_path}")


if __name__ == "__main__":
    main()
