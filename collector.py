#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import json
import os
import platform
import re
import ssl
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.json"
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "agri_items.sqlite3"
ITEMS_JSON = DATA_DIR / "items.json"
SUMMARY_JSON = DATA_DIR / "summary.json"

USER_AGENT = "AgriInfoHub/0.1 (+local personal collector)"
CATEGORY_LABELS = {
    "news": "농업 뉴스",
    "plant_reviews": "식물 리뷰",
    "support": "지원사업",
}

SUPPORT_HINTS = ["지원", "보조", "융자", "공모", "신청", "모집", "접수", "사업", "농업기술센터", "농식품부"]
PLANT_REVIEW_HINTS = ["후기", "리뷰", "식집사", "반려식물", "실내식물", "분갈이", "키우기", "물주기"]
NEWS_HINTS = ["농업", "농촌", "작물", "재배", "병해충", "기후", "스마트팜", "농산물"]
QUALITY_BLOCK_TERMS = [
    "바로가기",
    "직원목록",
    "조직도",
    "오시는 길",
    "모바일웹",
    "사이트맵",
    "개인정보처리방침",
    "저작권",
    "로그인",
    "회원가입",
    "주간업무일정",
    "월간업무일정",
    "국립원예특작과학원 /",
    " / ",
    "농업기술데이터플랫폼",
    "[포토]",
    "기고",
    "선박",
    "일손돕기",
    "발대",
    "행사 성료",
    "프로그램 운영",
    "채용후보자",
    "최종합격자",
    "서류전형",
    "면접시험",
    "기간제근로자",
    "전문임기제",
    "일반직공무원",
    "네이버 블로그",
    "Naver Blog",
    "브런치",
    "쿠팡",
    "가격비교",
    "할인",
    "쿠폰",
    "광고",
    "협찬",
    "로또",
    "코인",
    "주식",
    "부동산",
]
QUALITY_ALLOW_TERMS = [
    "보도자료",
    "공고",
    "지원",
    "신청",
    "모집",
    "사업",
    "재배",
    "병해충",
    "방제",
    "농업기술",
    "스마트팜",
    "청년농",
    "귀농",
    "농산물",
    "가격",
    "반려식물",
    "실내식물",
    "분갈이",
    "물주기",
    "키우기",
]


@dataclass
class CollectedItem:
    id: str
    title: str
    url: str
    source: str
    category: str
    published_at: str | None
    collected_at: str
    summary: str
    keywords: list[str]
    importance: int


class LinkExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self._current_href: str | None = None
        self._current_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a" or self._current_href is not None:
            return
        attr_map = {key.lower(): value for key, value in attrs}
        href = attr_map.get("href")
        if href:
            self._current_href = href
            self._current_text = []

    def handle_data(self, data: str) -> None:
        if self._current_href is not None:
            self._current_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._current_href is not None:
            text = clean_text(" ".join(self._current_text))
            if text:
                self.links.append((self._current_href, text))
            self._current_href = None
            self._current_text = []


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def clean_text(value: str | None) -> str:
    if not value:
        return ""
    value = html.unescape(value)
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def stable_id(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]


def is_public_http_url(value: str) -> bool:
    if re.search(r"\s", value):
        return False
    parsed = urllib.parse.urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def normalize_public_url(href: str, base_url: str = "") -> str | None:
    href = clean_text(href).strip()
    if not href:
        return None
    if href.lower().startswith(("javascript:", "mailto:", "tel:", "#")):
        return None
    url = urllib.parse.urljoin(base_url, href).strip()
    if not is_public_http_url(url):
        return None
    return url


def parse_date(value: str | None) -> str | None:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt.timezone.utc)
        return parsed.astimezone(dt.timezone.utc).isoformat()
    except (TypeError, ValueError):
        return None


def load_config() -> dict[str, Any]:
    with CONFIG_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def mac_display_is_awake() -> bool:
    if platform.system() != "Darwin":
        return True
    try:
        result = subprocess.run(
            ["ioreg", "-n", "IODisplayWrangler", "-r"],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
        match = re.search(r'"DevicePowerState"\s*=\s*(\d+)', result.stdout)
        if match:
            return int(match.group(1)) >= 4
    except (OSError, subprocess.SubprocessError):
        pass
    return True


def fetch_url(url: str, allow_insecure_ssl_fallback: bool = False) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/rss+xml, application/xml, text/xml, text/html;q=0.9, */*;q=0.5",
            "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.5",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.read()
    except urllib.error.URLError as exc:
        if not allow_insecure_ssl_fallback or "CERTIFICATE_VERIFY_FAILED" not in str(exc):
            raise
        insecure_context = ssl._create_unverified_context()
        with urllib.request.urlopen(request, timeout=20, context=insecure_context) as response:
            return response.read()


def child_text(element: ET.Element, names: list[str]) -> str:
    for name in names:
        child = element.find(name)
        if child is not None and child.text:
            return clean_text(child.text)
        child = element.find(f"{{*}}{name}")
        if child is not None and child.text:
            return clean_text(child.text)
    return ""


def child_link(element: ET.Element) -> str:
    direct = child_text(element, ["link"])
    if direct:
        return direct
    for child in element.findall("{*}link"):
        href = child.attrib.get("href")
        if href:
            return href
    return ""


def classify_item(text: str, source_category: str) -> str:
    lowered = text.lower()
    if any(term.lower() in lowered for term in SUPPORT_HINTS):
        return "support"
    if any(term.lower() in lowered for term in PLANT_REVIEW_HINTS):
        return "plant_reviews"
    if source_category in CATEGORY_LABELS:
        return source_category
    return "news"


def extract_keywords(text: str, config: dict[str, Any]) -> list[str]:
    candidates: list[str] = []
    for terms in config.get("watch_terms", {}).values():
        candidates.extend(terms)
    candidates.extend(SUPPORT_HINTS + PLANT_REVIEW_HINTS + NEWS_HINTS)

    found: list[str] = []
    lowered = text.lower()
    for term in candidates:
        if term.lower() in lowered and term not in found:
            found.append(term)
    return found[:8]


def summarize(title: str, body: str) -> str:
    text = clean_text(body)
    if not text:
        return title
    if len(text) <= 180:
        return text
    return text[:177].rstrip() + "..."


def score_importance(text: str, category: str, source_name: str) -> int:
    score = 42
    important_terms = ["마감", "신청", "모집", "공고", "지원", "보조", "융자", "재해", "병해충", "가격", "급등", "청년농"]
    score += sum(6 for term in important_terms if term in text)
    if category == "support":
        score += 16
    if any(name in source_name for name in ["농식품부", "농사로", "농업기술센터"]):
        score += 10
    return max(0, min(score, 100))


def comparable_title(value: str) -> str:
    value = re.sub(r"\s+-\s+[^-]+$", "", value)
    value = re.sub(r"[\[\]“”\"'‘’…·,.:;!?()\s]+", "", value)
    return value.lower()


def passes_quality_filter(title: str, summary: str, category: str, keywords: list[str]) -> bool:
    text = f"{title} {summary}"
    if any(term.lower() in text.lower() for term in QUALITY_BLOCK_TERMS):
        return False

    if category == "support":
        return any(term in text for term in ["지원", "보조", "융자", "공모", "신청", "모집", "사업", "공고"])

    if category == "plant_reviews":
        return any(term in text for term in ["반려식물", "식물", "실내식물", "분갈이", "물주기", "키우기", "다육", "몬스테라", "허브"])

    if keywords:
        return True
    return any(term in text for term in QUALITY_ALLOW_TERMS)


def parse_feed(raw: bytes, source: dict[str, Any], config: dict[str, Any]) -> list[CollectedItem]:
    root = ET.fromstring(raw)
    nodes = root.findall(".//item")
    if not nodes:
        nodes = root.findall(".//{*}entry")

    collected_at = now_iso()
    items: list[CollectedItem] = []
    for node in nodes[:80]:
        title = child_text(node, ["title"])
        url = normalize_public_url(child_link(node))
        description = child_text(node, ["description", "summary", "content", "encoded"])
        published_at = parse_date(child_text(node, ["pubDate", "published", "updated"]))

        if not title or not url:
            continue

        full_text = f"{title} {description}"
        category = classify_item(full_text, source.get("category", "news"))
        keywords = extract_keywords(full_text, config)
        summary = summarize(title, description)
        if not passes_quality_filter(title, summary, category, keywords):
            continue
        item_id = stable_id(url or f"{title}:{published_at}")

        items.append(
            CollectedItem(
                id=item_id,
                title=title,
                url=url,
                source=source["name"],
                category=category,
                published_at=published_at,
                collected_at=collected_at,
                summary=summary,
                keywords=keywords,
                importance=score_importance(full_text, category, source["name"]),
            )
        )
    return items


def parse_html_links(raw: bytes, source: dict[str, Any], config: dict[str, Any]) -> list[CollectedItem]:
    text = raw.decode("utf-8", errors="replace")
    parser = LinkExtractor()
    parser.feed(text)

    include_terms = source.get("include_terms") or []
    collected_at = now_iso()
    items: list[CollectedItem] = []
    seen_urls: set[str] = set()

    for href, title in parser.links:
        if len(title) < 7:
            continue
        if include_terms and not any(term in title for term in include_terms):
            continue

        url = normalize_public_url(href, source["url"])
        if not url:
            continue
        if url in seen_urls:
            continue
        seen_urls.add(url)

        category = classify_item(title, source.get("category", "news"))
        keywords = extract_keywords(title, config)
        if not passes_quality_filter(title, title, category, keywords):
            continue
        items.append(
            CollectedItem(
                id=stable_id(url),
                title=title,
                url=url,
                source=source["name"],
                category=category,
                published_at=None,
                collected_at=collected_at,
                summary=title,
                keywords=keywords,
                importance=score_importance(title, category, source["name"]),
            )
        )
    return items[:80]


def ensure_database() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS items (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                source TEXT NOT NULL,
                category TEXT NOT NULL,
                published_at TEXT,
                collected_at TEXT NOT NULL,
                summary TEXT NOT NULL,
                keywords TEXT NOT NULL,
                importance INTEGER NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_items_category ON items(category)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_items_collected_at ON items(collected_at)")


def save_items(items: list[CollectedItem]) -> int:
    ensure_database()
    new_count = 0
    with sqlite3.connect(DB_PATH) as conn:
        for item in items:
            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO items (
                    id, title, url, source, category, published_at, collected_at, summary, keywords, importance
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item.id,
                    item.title,
                    item.url,
                    item.source,
                    item.category,
                    item.published_at,
                    item.collected_at,
                    item.summary,
                    json.dumps(item.keywords, ensure_ascii=False),
                    item.importance,
                ),
            )
            new_count += cursor.rowcount
    return new_count


def rows_to_items(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    seen_titles: set[str] = set()
    for row in rows:
        item = dict(row)
        if not is_public_http_url(item.get("url", "")):
            continue
        try:
            item["keywords"] = json.loads(item["keywords"])
        except json.JSONDecodeError:
            item["keywords"] = []
        if not passes_quality_filter(item["title"], item["summary"], item["category"], item["keywords"]):
            continue
        title_key = comparable_title(item["title"])
        if title_key in seen_titles:
            continue
        seen_titles.add(title_key)
        item["category_label"] = CATEGORY_LABELS.get(item["category"], item["category"])
        items.append(item)
    return items


def build_stats(items: list[dict[str, Any]]) -> dict[str, Any]:
    category_counts = {key: 0 for key in CATEGORY_LABELS}
    keyword_counts: dict[str, int] = {}
    sources: dict[str, int] = {}

    for item in items:
        category_counts[item["category"]] = category_counts.get(item["category"], 0) + 1
        sources[item["source"]] = sources.get(item["source"], 0) + 1
        for keyword in item.get("keywords", []):
            keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1

    top_keywords = sorted(keyword_counts.items(), key=lambda pair: pair[1], reverse=True)[:12]
    top_sources = sorted(sources.items(), key=lambda pair: pair[1], reverse=True)[:10]
    return {
        "total": len(items),
        "category_counts": category_counts,
        "top_keywords": [{"keyword": key, "count": count} for key, count in top_keywords],
        "top_sources": [{"source": key, "count": count} for key, count in top_sources],
    }


def export_json(run_meta: dict[str, Any]) -> None:
    ensure_database()
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT id, title, url, source, category, published_at, collected_at, summary, keywords, importance
            FROM items
            WHERE url LIKE 'http://%' OR url LIKE 'https://%'
            ORDER BY COALESCE(published_at, collected_at) DESC
            LIMIT 1000
            """
        ).fetchall()

    items = rows_to_items(rows)
    payload = {
        "generated_at": now_iso(),
        "items": items,
        "stats": build_stats(items),
        "run": run_meta,
    }
    ITEMS_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    SUMMARY_JSON.write_text(json.dumps({"generated_at": payload["generated_at"], **payload["stats"], "run": run_meta}, ensure_ascii=False, indent=2), encoding="utf-8")


def collect_once(ignore_display: bool = False) -> int:
    config = load_config()
    display_awake = mac_display_is_awake()
    should_respect_display = bool(config.get("respect_display_state", True)) and not ignore_display

    if should_respect_display and not display_awake:
        run_meta = {
            "status": "skipped_display_asleep",
            "display_awake": display_awake,
            "new_items": 0,
            "errors": [],
        }
        export_json(run_meta)
        print("Skipped: display appears to be asleep.")
        return 0

    all_items: list[CollectedItem] = []
    errors: list[dict[str, str]] = []

    for source in config.get("sources", []):
        try:
            raw = fetch_url(source["url"], bool(config.get("allow_insecure_ssl_fallback", False)))
            if source.get("type") == "html_links":
                items = parse_html_links(raw, source, config)
            else:
                items = parse_feed(raw, source, config)
            all_items.extend(items)
            print(f"{source['name']}: {len(items)} items")
        except (urllib.error.URLError, TimeoutError, ET.ParseError, OSError, ValueError) as exc:
            message = str(exc)
            errors.append({"source": source.get("name", "unknown"), "error": message})
            print(f"{source.get('name', 'unknown')}: failed: {message}", file=sys.stderr)

    new_count = save_items(all_items)
    run_meta = {
        "status": "ok" if not errors else "partial",
        "display_awake": display_awake,
        "new_items": new_count,
        "fetched_items": len(all_items),
        "errors": errors,
    }
    export_json(run_meta)
    print(f"Saved {new_count} new items. Exported {ITEMS_JSON}.")
    return 0 if not errors else 2


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect agriculture information and export dashboard data.")
    parser.add_argument("--once", action="store_true", help="Run one collection cycle.")
    parser.add_argument("--loop", action="store_true", help="Keep collecting at the configured interval.")
    parser.add_argument("--ignore-display", action="store_true", help="Collect even if the display appears asleep.")
    args = parser.parse_args()

    if not args.once and not args.loop:
        args.once = True

    if args.loop:
        config = load_config()
        interval = max(5, int(config.get("collection_interval_minutes", 30))) * 60
        while True:
            collect_once(ignore_display=args.ignore_display)
            time.sleep(interval)

    return collect_once(ignore_display=args.ignore_display)


if __name__ == "__main__":
    raise SystemExit(main())
