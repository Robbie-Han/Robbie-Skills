#!/bin/bash

# Article Saver Setup Script
# 用于一键配置环境

echo "🔍 检查 Python 环境..."
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到 python3，请先安装 Python"
    exit 1
fi

echo "📦 安装依赖库 (playwright, requests)..."
python3 -m pip install -r "$(dirname "$0")/requirements.txt"

echo "🌐 安装 Playwright 浏览器驱动 (Chromium)..."
python3 -m playwright install chromium

echo "✅ 环境配置完成！"
echo "你可以使用以下命令运行抓取工具："
echo "python3 scripts/saver.py <URL>"
