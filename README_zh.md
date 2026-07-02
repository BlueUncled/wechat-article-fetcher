# wechat-article-fetcher

<div align="center">
  <a href="README.md"><img src="https://img.shields.io/badge/🇬🇧_English-4A90D9?style=for-the-badge" alt="English"></a>
  &nbsp;
  <a href="README_zh.md"><img src="https://img.shields.io/badge/🇨🇳_中文-DE4A4A?style=for-the-badge" alt="中文"></a>
</div>

一键抓取微信公众号文章为**纯文本**，绕过微信浏览器验证码限制。

## 原理

微信文章（`mp.weixin.qq.com`）在自动化浏览器访问时会触发验证码（`wappoc_appmsgcaptcha`）。本工具巧妙利用以下机制绕过：

1. **搜狗微信搜索** — 通过[搜狗微信搜索引擎](https://weixin.sogou.com/)（唯一索引微信公众号的搜索引擎）按关键词查找文章
2. **验证码 URL 提取** — 用 Playwright + stealth 访问搜狗跳转链接，微信触发验证码，但验证码 URL 中的 `target_url` 参数暴露了**真实的签名文章 URL**
3. **直接抓取** — 用 `requests` 直接请求真实 URL。微信验证码只拦截浏览器，不拦截 HTTP 客户端 — 所以 `requests` 能顺利通过
4. **纯文本输出** — 解析 HTML 提取纯文字，无标签、无图片、无链接

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐     ┌──────────────┐
│ 搜狗微信搜索 │────▶│ Playwright+Stealth│────▶│ 从验证码URL提取  │────▶│ requests GET │
│  (关键词)    │     │   (定位文章)      │     │  真实文章URL     │     │  (获取内容)   │
└─────────────┘     └──────────────────┘     └─────────────────┘     └──────────────┘
```

## 安装

### 一键安装（作为 Claude Code Skill）

```bash
git clone https://github.com/BlueUncled/wechat-article-fetcher.git /tmp/wechat-article-fetcher
cd /tmp/wechat-article-fetcher && bash install.sh
```

安装完成后：
- 脚本自动复制到 `~/.claude/skills/wechat-article-fetcher/`
- 安装 Python 依赖（playwright、playwright-stealth、requests）
- 安装 Chromium 无头浏览器

### 手动安装

```bash
pip install -r requirements.txt
playwright install-deps chromium
playwright install chromium
```

## 使用方法

### 命令行

```bash
# 按关键词搜索并输出纯文本
python wechat_article_fetcher.py "每日心语简报"

# 仅列出搜索结果，不抓取内容
python wechat_article_fetcher.py "每日心语简报" --list

# 抓取指定结果（0 起始）
python wechat_article_fetcher.py "每日心语简报" --index 0

# 输出为 JSON 格式
python wechat_article_fetcher.py "每日心语简报" --json

# 直接通过微信文章 URL 抓取
python wechat_article_fetcher.py --url "https://mp.weixin.qq.com/s/xxxxx"
```

### Python 模块

```python
from wechat_article_fetcher import fetch_by_keyword, fetch_by_url, search_sogou

# 搜索并抓取第一条结果
result = fetch_by_keyword("每日心语简报")
print(result["title"])   # 文章标题
print(result["text"])    # 纯文本正文
print(result["url"])     # 微信文章链接
print(result["date"])    # 抓取日期

# 抓取指定结果
result = fetch_by_keyword("每日心语简报", index=2)

# 直接通过 URL 抓取
result = fetch_by_url("https://mp.weixin.qq.com/s/xxxxx")

# 仅列出搜索结果
results = search_sogou("每日心语简报")
for i, r in enumerate(results):
    print(f"[{i}] {r['title']}  ({r['source']})")
    print(f"    {r['summary']}")
```

### Claude Code Skill

运行 `install.sh` 后，可直接在 Claude Code 中使用：

```
帮我抓取"每日心语简报"的公众号文章
```

或直接触发：

```
/wechat-article-fetcher
```

## 输出示例

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

JSON 输出（`--json`）：

```json
{
  "title": "心语简报，工作愉快|2026-7-2",
  "text": "美好的一天，从读报开始...",
  "url": "https://mp.weixin.qq.com/s?src=11&timestamp=...",
  "date": "2026-07-02"
}
```

## API 参考

| 函数 | 说明 |
|------|------|
| `fetch_by_keyword(keyword, index=0)` | 搜狗搜索并按关键词抓取文章 |
| `fetch_by_url(url)` | 直接通过微信 URL 抓取文章 |
| `fetch_by_sogou_url(sogou_url)` | 通过搜狗跳转 URL 抓取文章 |
| `search_sogou(keyword)` | 仅搜索，返回结果列表（不抓取内容） |

所有抓取函数返回：`{"title": str, "text": str, "url": str, "date": str}`

## 依赖

| 包 | 用途 |
|----|------|
| `playwright` | 无头 Chromium，用于搜狗搜索和 URL 解析 |
| `playwright-stealth` | Chromium 反检测 |
| `requests` | 直接 HTTP 抓取文章内容 |

## 注意事项

- 搜狗微信搜索偶尔会触发反爬验证码，等几分钟后重试即可
- 验证码中提取的签名 URL 有时效性，提取后需尽快抓取
- 本工具仅输出**纯文本** — 无图片、无 HTML 格式、无超链接
- 搜狗是唯一索引微信公众号的搜索引擎，搜狗不可用时则无法替代

## License

MIT
