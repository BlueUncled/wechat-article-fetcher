# wechat-article-fetcher

<div align="center">
  <a href="README.md"><img src="https://img.shields.io/badge/🇬🇧_English-4A90D9?style=for-the-badge" alt="English"></a>
  &nbsp;
  <a href="README_zh.md"><img src="https://img.shields.io/badge/🇨🇳_中文-DE4A4A?style=for-the-badge" alt="中文"></a>
</div>

Fetch WeChat (微信) public account articles as **plain text**, bypassing WeChat's browser-based captcha.

## How It Works

WeChat articles (`mp.weixin.qq.com`) normally trigger a captcha (`wappoc_appmsgcaptcha`) when accessed by automated browsers. This tool uses a clever workaround:

1. **Sogou WeChat Search** — Use [Sogou's WeChat search engine](https://weixin.sogou.com/) (the only search engine that indexes WeChat public accounts) to find articles by keyword.
2. **Captcha URL Extraction** — Navigate to the Sogou redirect link via Playwright + stealth. WeChat triggers its captcha, but the captcha URL contains a `target_url` parameter with the **real signed article URL**.
3. **Direct Fetch** — Use `requests` to fetch the article content from the real URL. WeChat's captcha only blocks browsers, not HTTP clients — so `requests` passes through cleanly.
4. **Plain Text Output** — Parse the HTML and extract clean text. No HTML tags, no images, no links — just the article content.

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐     ┌──────────────┐
│ Sogou Search │────▶│ Playwright+Stealth│────▶│ Extract URL from │────▶│ requests GET │
│  (keyword)   │     │  (find article)   │     │  captcha URL     │     │ (get content)│
└─────────────┘     └──────────────────┘     └─────────────────┘     └──────────────┘
```

## Installation

### One-click Install (as Claude Code Skill)

```bash
git clone https://github.com/BlueUncled/wechat-article-fetcher.git /tmp/wechat-article-fetcher
cd /tmp/wechat-article-fetcher && bash install.sh
```

This will:
- Copy the script to `~/.claude/skills/wechat-article-fetcher/`
- Install Python dependencies (playwright, playwright-stealth, requests)
- Install Chromium browser for headless browsing

### Manual Install

```bash
pip install -r requirements.txt
playwright install-deps chromium
playwright install chromium
```

## Usage

### Command Line

```bash
# Search by keyword and print plain text
python wechat_article_fetcher.py "每日心语简报"

# List search results without fetching
python wechat_article_fetcher.py "每日心语简报" --list

# Fetch a specific result (0-based index)
python wechat_article_fetcher.py "每日心语简报" --index 0

# Output as JSON
python wechat_article_fetcher.py "每日心语简报" --json

# Fetch directly from a WeChat article URL
python wechat_article_fetcher.py --url "https://mp.weixin.qq.com/s/xxxxx"
```

### Python Module

```python
from wechat_article_fetcher import fetch_by_keyword, fetch_by_url, search_sogou

# Search and fetch the first result
result = fetch_by_keyword("每日心语简报")
print(result["title"])   # Article title
print(result["text"])    # Full plain text content
print(result["url"])     # WeChat article URL
print(result["date"])    # Fetch date

# Fetch a specific result
result = fetch_by_keyword("每日心语简报", index=2)

# Fetch directly from URL
result = fetch_by_url("https://mp.weixin.qq.com/s/xxxxx")

# Only list search results
results = search_sogou("每日心语简报")
for i, r in enumerate(results):
    print(f"[{i}] {r['title']}  ({r['source']})")
    print(f"    {r['summary']}")
```

### Claude Code Skill

After running `install.sh`, you can use this as a Claude Code skill. Just say:

```
帮我抓取"每日心语简报"的公众号文章
```

Or trigger it directly:

```
/wechat-article-fetcher
```

## Output Format

```
Title: 心语简报，工作愉快|2026-7-2
URL: https://mp.weixin.qq.com/s?src=11&timestamp=...
Date: 2026-07-02
------------------------------------------------------------
美好的一天，从读报开始，7月2日，丙午年五月十八，星期四，工作愉快，幸福生活
1、全球最火存储ETF纳入中国芯片龙头，规模已突破200亿美元；
2、樊振东正式加盟德甲杜塞尔多夫俱乐部；
...
【心语】世界弥漫着焦躁不安的气息...
【生活小常识】
...
【历史上的今天】
626年——...
```

With `--json`:

```json
{
  "title": "心语简报，工作愉快|2026-7-2",
  "text": "美好的一天，从读报开始...",
  "url": "https://mp.weixin.qq.com/s?src=11&timestamp=...",
  "date": "2026-07-02"
}
```

## API Reference

| Function | Description |
|----------|-------------|
| `fetch_by_keyword(keyword, index=0)` | Search Sogou and fetch article by keyword |
| `fetch_by_url(url)` | Fetch article directly from WeChat URL |
| `fetch_by_sogou_url(sogou_url)` | Fetch article from a Sogou redirect URL |
| `search_sogou(keyword)` | Search Sogou and return result list (without fetching) |

All fetch functions return: `{"title": str, "text": str, "url": str, "date": str}`

## Dependencies

| Package | Purpose |
|---------|---------|
| `playwright` | Headless Chromium for Sogou search and URL resolution |
| `playwright-stealth` | Anti-bot-detection for Chromium |
| `requests` | Direct HTTP fetch for article content |

## Limitations

- Sogou WeChat search may occasionally trigger its own antispider captcha — retry after a few minutes.
- The signed article URL from the captcha has a limited validity period. Fetch promptly after extraction.
- This tool extracts **plain text only** — no images, no HTML formatting, no hyperlinks.
- Sogou is the only search engine that indexes WeChat public accounts. If Sogou is down, there is no alternative.

## License

MIT
