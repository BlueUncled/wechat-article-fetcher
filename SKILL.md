---
name: wechat-article-fetcher
description: 抓取微信公众号文章纯文本内容。通过搜狗微信搜索或直接URL获取文章，输出纯文字（无HTML/图片/链接）。当用户需要获取微信公众号文章内容、抓取公众号文章正文时使用此技能。
---

# 微信公众号文章抓取器

## 触发条件

当用户说以下类似内容时触发：
- "帮我抓一篇公众号文章"
- "获取这个公众号的内容"
- "抓取微信文章"
- "搜索公众号文章并获取内容"

## 依赖

需要安装以下依赖（首次使用执行 install.sh）：

```bash
pip install playwright playwright-stealth requests
playwright install chromium
playwright install-deps chromium
```

## 工作流程

### 方式一：按关键词搜索并抓取

```bash
python3 ~/.claude/skills/wechat-article-fetcher/wechat_article_fetcher.py "关键词" --json
```

参数：
- 第一个参数：搜索关键词（必填）
- `--index N`：选择第 N 个搜索结果（默认 0，即第一个/最新的）
- `--json`：输出 JSON 格式（推荐，方便后续处理）
- `--list`：仅列出搜索结果，不抓取内容

### 方式二：直接通过 URL 抓取

```bash
python3 ~/.claude/skills/wechat-article-fetcher/wechat_article_fetcher.py --url "https://mp.weixin.qq.com/s/xxxxx" --json
```

### 输出格式

```json
{
  "title": "文章标题",
  "text": "文章纯文本内容（无HTML标签）",
  "url": "微信文章URL",
  "date": "抓取日期"
}
```

## 作为 Python 模块使用

```python
import sys
sys.path.insert(0, "/home/dindin/.claude/skills/wechat-article-fetcher")
from wechat_article_fetcher import fetch_by_keyword, fetch_by_url

result = fetch_by_keyword("每日心语简报")
print(result["text"])
```

## 常见问题

- **搜狗 antispider**：频繁请求会触发搜狗反爬，等几分钟后重试
- **微信环境异常**：签名URL有时效性，抓取到URL后需立即使用
- **无结果**：更换关键词重试，搜狗是唯一索引微信公众号的搜索引擎

## 注意事项

- 仅输出纯文本，不含 HTML、图片、链接
- 搜狗微信搜索是唯一可索引微信公众号的搜索引擎
- 本工具仅用于学习和研究目的，请勿用于商业用途或大规模爬取
