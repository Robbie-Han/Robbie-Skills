---
name: article-saver
description: 专门用于抓取和保存微信公众号、X (Twitter)、知乎的文章工具。支持自动按平台分类存储、保持图片/GIF原画质量，并保存为干净的 Markdown 格式。
---

# Article Saver

## 概述

`article-saver` 是一个高效的文章抓取和本地化保存工具，特别针对微信公众号、X (Twitter) 和知乎进行了优化。它能自动识别平台，将内容整理为 Markdown，并将所有图片和 GIF 以原始质量下载到本地，按平台进行分类管理。

## 核心功能

- **平台自动分类**：保存路径为 `Documents/WebContent/素材/{平台名称}/{日期}_{标题}/`。
- **高质量图片**：自动尝试获取 X 的 large 原图，保持微信和知乎的图片及 GIF 原始质量。
- **纯净内容**：剔除网页多余的侧边栏、广告和互动数据，只保留正文。
- **Markdown 格式**：生成的 `content.md` 包含 YAML 元数据（标题、作者、来源、URL）。

## 支持平台

| 平台 | 特色处理 |
| :--- | :--- |
| **微信公众号** | 支持懒加载图片识别，支持独立维护登录态。 |
| **X (Twitter)** | 支持长推文抓取，自动将媒体链接转换为 `:large` 原图。 |
| **知乎** | 支持回答（Answer）和专栏（Zhuanlan）两种模式的正文提取，支持独立维护登录态。 |

## 使用方式

### 直接通过 URL 调用
只需提供文章链接，技能会自动识别平台并执行保存。

```
帮我保存这篇文章：https://mp.weixin.qq.com/s/xxxxxx
```

### 身份认证设置 (仅需一次)
部分平台（微信、知乎）可能需要登录才能获取完整内容：
- **微信**: `python3 scripts/setup_wechat.py`
- **知乎**: `python3 scripts/setup_zhihu.py`

### 命令行手动运行
```bash
python3 scripts/saver.py <URL>
```

## 资源说明

- **scripts/saver.py**: 核心逻辑脚本，基于 Playwright 实现，处理内容提取和图片下载。
- **scripts/setup_wechat.py**: 微信登录态设置工具。
- **scripts/setup_zhihu.py**: 知乎登录态设置工具。
- **data/**: 存储登录凭证和临时数据。

## 注意事项

1. **Playwright 依赖**：如果提示缺少驱动，请运行 `playwright install chromium`。
2. **登录态管理**：如果遇到反爬虫限制（如 403 或验证码），请运行对应的 `setup_*.py` 脚本完成扫码登录。
3. **GIF 格式**：脚本会自动通过 Content-Type 识别并保存 `.gif` 后缀，确保动态图正常。
