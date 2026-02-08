# Article-Saver Skill Development Summary

## 1. 核心目标
创建一个**独立、自包含**的 Claude 技能 `article-saver`，用于从 **微信公众号**、**X (Twitter)** 和 **知乎** 抓取文章并保存到本地。
*   **目标路径**：`/Users/a123/Documents/WebContent/素材/{平台}/{日期}_{标题}/`
*   **核心特性**：
    *   自动平台分类与归档。
    *   下载并保留**原始质量**的图片和 GIF。
    *   生成干净的 Markdown 正文（剔除广告/侧边栏）。
    *   **零外部依赖**（已与 `url-reader` 完全解耦）。

## 2. 已完成的关键工作
*   **技能架构**：
    *   目录结构：`/Users/a123/.claude/skills/article-saver/`
    *   已打包交付物：`/Users/a123/.claude/skills/dist/article-saver.skill`
*   **核心代码 (`scripts/saver.py`)**：
    *   **平台适配**：
        *   ✅ **微信公众号**：支持懒加载图片，支持 Cookie 登录。
        *   ✅ **X (Twitter)**：支持长文/推文，自动解析 `:large` 原图，修复了 DOM 选择器。
        *   ✅ **知乎**：支持回答/专栏，**集成 Jina Reader 自动降级策略**（应对 403），支持 Cookie 登录。
    *   **功能实现**：
        *   自动创建层级目录。
        *   基于 Playwright 的无头浏览器抓取。
        *   图片/GIF 原画质下载与本地化引用替换。
*   **辅助工具**：
    *   `scripts/setup_wechat.py`：独立管理微信登录态。
    *   `scripts/setup_zhihu.py`：独立管理知乎登录态。
*   **文档**：
    *   `SKILL.md`：已更新，移除对 `url-reader` 的依赖描述，添加独立使用说明。

## 3. 当前卡点或未解决问题
*   **知乎反爬验证**：
    *   知乎对无登录态的自动化访问限制极严（Playwright 和 Jina Reader 均可能触发 403）。
    *   **已实现解决方案**：代码已包含 `setup_zhihu.py` 脚本，允许用户手动扫码登录保存 Cookie。
    *   **待验证**：代码逻辑已就绪，但用户尚未实际运行 `setup_zhihu.py` 生成 `data/zhihu_auth.json`，因此在无 Cookie 环境下仍可能触发 Jina 降级或失败。

## 4. 下一步建议行动
1.  **用户侧配置**：
    *   运行 `python3 scripts/setup_wechat.py` 获取微信登录态。
    *   运行 `python3 scripts/setup_zhihu.py` 获取知乎登录态。
2.  **最终集成测试**：
    *   在配置好 Cookie 后，再次运行 `saver.py` 测试知乎专栏链接，确认是否能通过 Playwright 直接抓取（优于 Jina 降级）。
3.  **分发**：
    *   将 `.skill` 文件分发给最终用户或部署到目标环境。

## 5. 已确认的重要决策与约束
*   **独立性**：`article-saver` 必须是独立的，不依赖 `url-reader` 的虚拟环境或数据文件。
*   **图片策略**：优先使用浏览器上下文 (`page.evaluate` + `fetch`) 下载图片，以确保获取到与渲染一致的资源（避免防盗链问题）。
*   **降级策略**：知乎抓取失败时，优先降级到 Jina Reader API，而不是直接报错。
*   **存储规范**：文件名必须经过清洗（`sanitize_filename`），避免因特殊字符导致文件系统错误。
