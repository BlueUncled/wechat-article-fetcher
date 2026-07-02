#!/bin/bash
set -e

SKILL_DIR="$HOME/.claude/skills/wechat-article-fetcher"

echo "=== wechat-article-fetcher 一键安装 ==="
echo ""

# 1. 创建 skill 目录
echo "[1/4] 创建 skill 目录..."
mkdir -p "$SKILL_DIR"

# 2. 复制文件
echo "[2/4] 复制脚本和配置文件..."
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cp "$SCRIPT_DIR/wechat_article_fetcher.py" "$SKILL_DIR/"
cp "$SCRIPT_DIR/SKILL.md" "$SKILL_DIR/"
cp "$SCRIPT_DIR/requirements.txt" "$SKILL_DIR/"

# 3. 安装 Python 依赖
echo "[3/4] 安装 Python 依赖..."
pip install playwright playwright-stealth requests

# 4. 安装 Chromium 浏览器
echo "[4/4] 安装 Chromium（首次安装需要几分钟）..."
playwright install chromium
playwright install-deps chromium 2>/dev/null || true

echo ""
echo "=== 安装完成 ==="
echo "Skill 目录: $SKILL_DIR"
echo ""
echo "使用方法:"
echo "  命令行: python3 $SKILL_DIR/wechat_article_fetcher.py \"关键词\""
echo "  模块:   from wechat_article_fetcher import fetch_by_keyword"
echo ""
echo "快速测试:"
echo "  python3 $SKILL_DIR/wechat_article_fetcher.py \"每日心语简报\" --list"
