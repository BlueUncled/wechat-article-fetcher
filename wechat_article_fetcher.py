#!/usr/bin/env python3
"""
wechat-article-fetcher - Fetch WeChat public account articles as plain text.

Bypasses WeChat's captcha by extracting the signed article URL from
Sogou's captcha redirect, then fetching content via requests.

Usage:
    # Search by keyword on Sogou WeChat search
    python wechat_article_fetcher.py "每日心语简报"

    # Fetch directly from a WeChat article URL
    python wechat_article_fetcher.py --url "https://mp.weixin.qq.com/s/xxxxx"

    # Output as JSON
    python wechat_article_fetcher.py "每日心语简报" --json

    # As a Python module
    from wechat_article_fetcher import search_and_fetch, fetch_by_keyword
    result = fetch_by_keyword("每日心语简报")
    print(result["text"])
"""
import argparse
import json
import re
import sys
from datetime import datetime
from html.parser import HTMLParser
from urllib.parse import unquote

import requests


# ---------------------------------------------------------------------------
# HTML → plain text converter (strips all tags, scripts, styles, links, images)
# ---------------------------------------------------------------------------
class PlainTextExtractor(HTMLParser):
    """Extract plain text from HTML, skipping scripts/styles."""

    def __init__(self):
        super().__init__()
        self.text: list[str] = []
        self._skip = False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip = True

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self._skip = False

    def handle_data(self, data):
        if not self._skip:
            t = data.strip()
            if t:
                self.text.append(t)


def html_to_text(html: str) -> str:
    """Convert HTML to plain text (no tags, no images, no links)."""
    extractor = PlainTextExtractor()
    extractor.feed(html)
    return "\n".join(extractor.text)


def extract_article_content(html: str) -> tuple[str, str]:
    """
    Extract title and body text from a WeChat article HTML page.

    Returns:
        (title, plain_text_body)
    """
    # Title: prefer the JS variable, fall back to <title>
    title_m = re.search(r'var\s+msg_title\s*=\s*["\'](.+?)["\']', html)
    if not title_m:
        title_m = re.search(r"<title>(.*?)</title>", html, re.DOTALL)
    title = title_m.group(1).strip() if title_m else ""

    # Body: extract from rich_media_content div
    content_m = re.search(
        r'<div class="rich_media_content[^>]*>(.*?)</div>\s*(?:<script|<div class="ct_mpda_wrp")',
        html,
        re.DOTALL,
    )
    if not content_m:
        content_m = re.search(
            r'<div class="rich_media_content[^>]*>(.*?)</div>', html, re.DOTALL
        )

    if content_m:
        body = html_to_text(content_m.group(1))
    else:
        # Fallback: extract entire body
        body_m = re.search(r"<body[^>]*>(.*?)</body>", html, re.DOTALL)
        body = html_to_text(body_m.group(1)) if body_m else html_to_text(html)

    return title, body


# ---------------------------------------------------------------------------
# Core fetching logic
# ---------------------------------------------------------------------------
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


def _get_stealth_context():
    """Create a Playwright browser context with stealth anti-detection."""
    from playwright.sync_api import sync_playwright
    from playwright_stealth import Stealth

    p = sync_playwright().start()
    stealth = Stealth()
    browser = p.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
    )
    context = browser.new_context(
        user_agent=HEADERS["User-Agent"],
        viewport={"width": 1920, "height": 1080},
        locale="zh-CN",
        timezone_id="Asia/Shanghai",
    )
    stealth.apply_stealth_sync(context)
    return p, browser, context


def _extract_article_url_from_captcha(captcha_url: str) -> str | None:
    """Extract the real article URL from WeChat's captcha redirect URL."""
    m = re.search(r"target_url=([^&]+)", captcha_url)
    if m:
        return unquote(m.group(1))
    # If already on article page
    if "mp.weixin.qq.com/s" in captcha_url:
        return captcha_url
    return None


def search_sogou(keyword: str) -> list[dict]:
    """
    Search Sogou WeChat search and return a list of article results.

    Each result has: {"title": str, "summary": str, "source": str, "sogou_url": str}
    """
    p, browser, context = _get_stealth_context()
    try:
        page = context.new_page()
        url = f"https://weixin.sogou.com/weixin?type=2&query={keyword}"
        page.goto(url, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(2000)

        if "antispider" in page.url:
            raise RuntimeError("Sogou antispider captcha triggered, please retry later")

        results = []
        items = page.query_selector_all("ul.news-list li")
        for item in items:
            title_el = item.query_selector("h3 a")
            summary_el = item.query_selector(".txt-info")
            source_el = item.query_selector(".s-p .all-time-y2")

            if not title_el:
                continue

            href = title_el.get_attribute("href") or ""
            if href.startswith("/"):
                href = "https://weixin.sogou.com" + href

            results.append(
                {
                    "title": title_el.inner_text().strip(),
                    "summary": (summary_el.inner_text().strip() if summary_el else ""),
                    "source": (source_el.inner_text().strip() if source_el else ""),
                    "sogou_url": href,
                }
            )

        return results
    finally:
        browser.close()
        p.stop()


def _fetch_article_html(article_url: str) -> str:
    """Fetch article HTML via requests (bypasses browser-based captcha)."""
    resp = requests.get(article_url, headers=HEADERS, timeout=15)
    if "环境异常" in resp.text:
        raise RuntimeError("WeChat blocked the request")
    return resp.text


def fetch_by_sogou_url(sogou_url: str) -> dict:
    """
    Given a Sogou redirect URL, resolve it to the WeChat article and fetch content.

    Returns:
        {"title": str, "text": str, "url": str, "date": str}
    """
    p, browser, context = _get_stealth_context()
    try:
        page = context.new_page()
        page.goto(sogou_url, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(5000)

        captcha_url = page.url
        article_url = _extract_article_url_from_captcha(captcha_url)
        if not article_url:
            raise RuntimeError(f"Could not extract article URL from: {captcha_url[:100]}")
    finally:
        browser.close()
        p.stop()

    html = _fetch_article_html(article_url)
    title, body = extract_article_content(html)

    return {
        "title": title,
        "text": body,
        "url": article_url,
        "date": datetime.now().strftime("%Y-%m-%d"),
    }


def fetch_by_keyword(keyword: str, index: int = 0) -> dict:
    """
    Search Sogou WeChat by keyword and fetch the article at the given index.

    Uses a single browser session for both search and URL resolution
    to avoid triggering Sogou's antispider on the second request.

    Args:
        keyword: Search query for Sogou WeChat search.
        index: Which result to fetch (0 = first/newest). Default 0.

    Returns:
        {"title": str, "text": str, "url": str, "date": str}
    """
    p, browser, context = _get_stealth_context()
    try:
        page = context.new_page()

        # Step 1: Search on Sogou
        search_url = f"https://weixin.sogou.com/weixin?type=2&query={keyword}"
        page.goto(search_url, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(2000)

        if "antispider" in page.url:
            raise RuntimeError("Sogou antispider captcha triggered, please retry later")

        items = page.query_selector_all("ul.news-list li")
        if not items:
            raise RuntimeError(f"No results found for: {keyword}")
        if index >= len(items):
            raise RuntimeError(
                f"Index {index} out of range, only {len(items)} results found"
            )

        # Step 2: Get the Sogou redirect link
        title_el = items[index].query_selector("h3 a")
        if not title_el:
            raise RuntimeError("Could not find article link in search result")
        href = title_el.get_attribute("href") or ""
        if href.startswith("/"):
            href = "https://weixin.sogou.com" + href

        # Step 3: Navigate to Sogou link → resolve to WeChat article URL
        page.goto(href, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(5000)

        captcha_url = page.url
        article_url = _extract_article_url_from_captcha(captcha_url)
        if not article_url:
            raise RuntimeError(f"Could not extract article URL from: {captcha_url[:100]}")

    finally:
        browser.close()
        p.stop()

    # Step 4: Fetch article content via requests
    html = _fetch_article_html(article_url)
    title, body = extract_article_content(html)

    return {
        "title": title,
        "text": body,
        "url": article_url,
        "date": datetime.now().strftime("%Y-%m-%d"),
    }


def fetch_by_url(wechat_url: str) -> dict:
    """
    Fetch a WeChat article directly by URL.

    If the URL triggers a captcha, attempts to extract the real URL from it.

    Args:
        wechat_url: A mp.weixin.qq.com article URL.

    Returns:
        {"title": str, "text": str, "url": str, "date": str}
    """
    # Try direct requests first
    try:
        html = _fetch_article_html(wechat_url)
        title, body = extract_article_content(html)
        if len(body) > 50:
            return {
                "title": title,
                "text": body,
                "url": wechat_url,
                "date": datetime.now().strftime("%Y-%m-%d"),
            }
    except RuntimeError:
        pass

    # If direct fetch fails, try via Playwright to resolve captcha
    p, browser, context = _get_stealth_context()
    try:
        page = context.new_page()
        page.goto(wechat_url, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(5000)

        final_url = page.url
        article_url = _extract_article_url_from_captcha(final_url) or wechat_url
    finally:
        browser.close()
        p.stop()

    html = _fetch_article_html(article_url)
    title, body = extract_article_content(html)
    return {
        "title": title,
        "text": body,
        "url": article_url,
        "date": datetime.now().strftime("%Y-%m-%d"),
    }


# Alias for convenience
search_and_fetch = fetch_by_keyword


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Fetch WeChat public account articles as plain text.",
        epilog="Example: python wechat_article_fetcher.py '每日心语简报'",
    )
    parser.add_argument(
        "keyword",
        nargs="?",
        help="Keyword to search on Sogou WeChat search",
    )
    parser.add_argument(
        "--url",
        help="Fetch directly from a WeChat article URL",
    )
    parser.add_argument(
        "--index",
        type=int,
        default=0,
        help="Which search result to fetch (0-based, default: 0)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON instead of plain text",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Only list search results without fetching content",
    )

    args = parser.parse_args()

    if not args.keyword and not args.url:
        parser.error("Either provide a keyword or --url")

    if args.url:
        result = fetch_by_url(args.url)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"Title: {result['title']}")
            print(f"URL: {result['url']}")
            print(f"Date: {result['date']}")
            print("-" * 60)
            print(result["text"])
        return

    # Search mode
    if args.list:
        results = search_sogou(args.keyword)
        for i, r in enumerate(results):
            print(f"[{i}] {r['title']}  ({r['source']})")
            print(f"    {r['summary'][:80]}")
            print()
        return

    result = fetch_by_keyword(args.keyword, index=args.index)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Title: {result['title']}")
        print(f"URL: {result['url']}")
        print(f"Date: {result['date']}")
        print("-" * 60)
        print(result["text"])


if __name__ == "__main__":
    main()
