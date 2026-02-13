#!/usr/bin/env python3
"""
Article Saver - 专注微信、X、知乎的文章抓取工具
功能：
1. 自动分平台存放：素材/{平台}/{日期}_{标题}/
2. 保持图片/GIF原画质量
3. 专注正文内容，剔除冗余元数据
"""

import os
import sys
import json
import asyncio
import requests
import re
import shutil
from urllib.parse import urlparse
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright

# 配置
DEFAULT_OUTPUT_ROOT = Path.home() / "Documents/WebContent/素材"
SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
DATA_DIR = SKILL_DIR / "data"
WECHAT_AUTH_FILE = DATA_DIR / "wechat_auth.json"
ZHIHU_AUTH_FILE = DATA_DIR / "zhihu_auth.json"

# 确保数据目录存在
DATA_DIR.mkdir(parents=True, exist_ok=True)

class ArticleSaver:
    def __init__(self, verbose=True):
        self.verbose = verbose
        self.output_root = DEFAULT_OUTPUT_ROOT
        self.mobile_ua = 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.38(0x18002629) NetType/WIFI Language/zh_CN'
        self.desktop_ua = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

    def log(self, msg):
        if self.verbose:
            print(msg)

    def identify_platform(self, url):
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        path = parsed.path.lower()

        if 'mp.weixin.qq.com' in domain:
            return '微信公众号', 'wechat'
        elif 'x.com' in domain or 'twitter.com' in domain:
            return 'X', 'x'
        elif 'zhihu.com' in domain:
            if 'zhuanlan' in domain:
                return '知乎专栏', 'zhihu'
            return '知乎', 'zhihu'
        return '其他', 'other'

    def sanitize_filename(self, name, max_length=50):
        name = re.sub(r'[<>:"/\\|?*\n\r\t]', '', name)
        name = re.sub(r'\s+', ' ', name).strip()
        if len(name) > max_length:
            name = name[:max_length]
        return name or "untitled"

    def read_with_jina(self, url):
        try:
            jina_url = f"https://r.jina.ai/{url}"
            headers = {
                'Accept': 'text/markdown',
                'User-Agent': self.desktop_ua
            }
            response = requests.get(jina_url, headers=headers, timeout=30)
            if response.status_code == 200:
                content = response.text
                if '环境异常' in content or '完成验证' in content or '403 Forbidden' in content:
                    return {'success': False, 'error': 'Jina 也无法绕过验证'}
                return {'success': True, 'content': content}
            return {'success': False, 'error': f'HTTP {response.status_code}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def extract_title_from_content(self, content):
        match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if match:
            return match.group(1).strip()
        return "Unknown_Title"

    def extract_images_from_content(self, content):
        return re.findall(r'!\[.*?\]\((https?://[^\s\)]+)\)', content)

    def download_image_requests(self, url, save_dir, index):
        try:
            headers = {'User-Agent': self.desktop_ua}
            # 处理防盗链
            if 'zhihu.com' in url or 'zhimg.com' in url:
                headers['Referer'] = 'https://www.zhihu.com/'

            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code == 200:
                content_type = response.headers.get('content-type', '')
                ext = '.jpg'
                if 'png' in content_type: ext = '.png'
                elif 'gif' in content_type: ext = '.gif'
                elif 'webp' in content_type: ext = '.webp'

                filename = f"img_{index:02d}{ext}"
                filepath = save_dir / filename
                filepath.write_bytes(response.content)
                return filename
        except Exception:
            pass
        return None

    async def scrape(self, url):
        platform_name, platform_id = self.identify_platform(url)
        self.log(f"📍 目标平台: {platform_name}")

        # 如果知乎被限制，尝试使用 Jina Reader 作为备选
        if platform_id == 'zhihu':
            self.log("🔄 知乎平台尝试使用 Jina Reader 策略...")
            jina_data = self.read_with_jina(url)
            if jina_data.get('success'):
                # 构造符合 extract_content 结构的数据
                title = self.extract_title_from_content(jina_data['content'])
                image_urls = self.extract_images_from_content(jina_data['content'])
                data = {
                    'title': title,
                    'author': '知乎用户',
                    'content': jina_data['content'],
                    'image_urls': image_urls
                }

                # Jina 返回的 markdown 中图片已经是 ![...](url) 格式
                # 我们需要下载这些图片并替换本地路径

                # 路径规划
                date_str = datetime.now().strftime("%Y-%m-%d")
                title_sanitized = self.sanitize_filename(title)
                folder_name = f"{date_str}_{title_sanitized}"
                save_dir = self.output_root / platform_name / folder_name
                save_dir.mkdir(parents=True, exist_ok=True)

                downloaded = []
                for i, img_url in enumerate(image_urls):
                    self.log(f"  ⬇️ 下载图片 [{i+1}/{len(image_urls)}]: {img_url[:50]}...")
                    local_name = self.download_image_requests(img_url, save_dir, i)
                    if local_name:
                        downloaded.append({"index": i, "filename": local_name, "temp_path": str(save_dir / local_name), "original_url": img_url})

                # 更新内容中的图片引用
                content = data['content']
                for img_info in downloaded:
                    # Jina 返回的 markdown 图片格式通常是 ![alt](url)
                    # 我们简单替换 url 为本地文件名
                    content = content.replace(img_info['original_url'], img_info['filename'])

                data['content'] = content

                # 直接保存，不需要再走 self.save 的移动逻辑，因为已经下载到目标目录了
                meta = f"""---
title: {data['title']}
author: {data['author']}
platform: {platform_name}
url: {url}
saved_at: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
---

"""
                md_file = save_dir / "content.md"
                md_file.write_text(meta + content, encoding='utf-8')
                self.log(f"\n✅ 已保存至: {save_dir}")

                return {"success": True, "data": data, "platform_name": platform_name, "platform_id": platform_id}

        async with async_playwright() as p:
            # 针对不同平台选择 UA
            ua = self.mobile_ua if platform_id == 'wechat' else self.desktop_ua
            browser = await p.chromium.launch(headless=True)

            # 加载登录态
            context_args = {"user_agent": ua}
            if platform_id == 'wechat' and WECHAT_AUTH_FILE.exists():
                context_args["storage_state"] = str(WECHAT_AUTH_FILE)
            elif platform_id == 'zhihu':
                if ZHIHU_AUTH_FILE.exists():
                    context_args["storage_state"] = str(ZHIHU_AUTH_FILE)
                    self.log("🔑 已加载知乎登录态")
                else:
                    self.log("⚠️ 未检测到知乎登录态 (data/zhihu_auth.json)，可能会触发反爬验证")

            context = await browser.new_context(**context_args)
            page = await context.new_page()

            # 针对知乎的特殊处理：知乎可能会有强反爬
            try:
                self.log(f"🌐 正在访问: {url}")
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)

                # 等待并处理可能的重定向或反爬
                if platform_id == 'zhihu':
                    await page.wait_for_timeout(3000)
                    if "liantong" in page.url or "captcha" in page.url:
                        self.log("⚠️ 检测到知乎验证码或跳转")

                await page.wait_for_timeout(2000)
            except Exception as e:
                self.log(f"⚠️ 页面加载异常: {str(e)}")

            # 调试：打印页面标题和当前 URL
            page_title = await page.title()
            current_url = page.url
            self.log(f"📄 页面标题: {page_title}")
            self.log(f"🔗 当前 URL: {current_url}")

            # 提取逻辑
            data = await self.extract_content(page, platform_id)

            if not data or not data.get('content'):
                # 记录失败时的 HTML 片段
                html = await page.content()
                self.log(f"⚠️ 提取失败。页面 HTML 长度: {len(html)}")
                if len(html) > 0:
                    self.log(f"⚠️ HTML 前 500 字: {html[:500]}")

                await browser.close()
                return {"success": False, "error": f"未能提取到有效内容 (标题: {page_title}, URL: {current_url})"}

            # 下载图片
            downloaded_images = await self.download_images(page, data['image_urls'], platform_id)
            data['downloaded_images'] = downloaded_images

            await browser.close()
            return {"success": True, "data": data, "platform_name": platform_name, "platform_id": platform_id}

    async def extract_content(self, page, platform_id):
        if platform_id == 'wechat':
            return await page.evaluate("""
                () => {
                    const title = document.querySelector('#activity-name')?.innerText?.trim() || '';
                    const author = document.querySelector('#js_name')?.innerText?.trim() || '';
                    const contentEl = document.querySelector('#js_content');
                    if (!contentEl) return null;

                    const image_urls = [];
                    const imgs = contentEl.querySelectorAll('img');
                    imgs.forEach((img, i) => {
                        let src = img.getAttribute('data-src') || img.getAttribute('src');
                        if (src && src.startsWith('http')) {
                            image_urls.push(src);
                            const placeholder = document.createTextNode(`{{IMG_${i}}}`);
                            img.parentNode.replaceChild(placeholder, img);
                        }
                    });

                    let markdown = contentEl.innerHTML
                        .replace(/<h[1-6][^>]*>(.*?)<\\/h[1-6]>/gi, (m, c) => `\\n## ${c.replace(/<[^>]+>/g, '')}\\n`)
                        .replace(/<p[^>]*>/gi, '\\n')
                        .replace(/<br[^>]*>/gi, '\\n')
                        .replace(/<strong[^>]*>(.*?)<\\/strong>/gi, '**$1**')
                        .replace(/<[^>]+>/g, '')
                        .replace(/\\n{3,}/g, '\\n\\n')
                        .trim();

                    return { title, author, content: markdown, image_urls };
                }
            """)
        elif platform_id == 'zhihu':
            return await page.evaluate("""
                () => {
                    let title = document.querySelector('.QuestionHeader-title')?.innerText ||
                                document.querySelector('.Post-Title')?.innerText ||
                                document.querySelector('h1')?.innerText || '';
                    let author = document.querySelector('.AuthorInfo-name')?.innerText ||
                                 document.querySelector('.UserLink-link')?.innerText || '';

                    // 知乎回答、文章或专栏正文
                    let contentEl = document.querySelector('.RichText.ztext') ||
                                    document.querySelector('.Post-RichTextContainer') ||
                                    document.querySelector('.Post-Content') ||
                                    document.querySelector('article');

                    if (!contentEl) return null;

                    const image_urls = [];
                    const imgs = contentEl.querySelectorAll('img');
                    imgs.forEach((img, i) => {
                        let src = img.getAttribute('data-actualsrc') ||
                                 img.getAttribute('data-original') ||
                                 img.getAttribute('src');
                        if (src && src.startsWith('http')) {
                            // 移除动态尺寸参数，获取原图
                            if (src.includes('?')) {
                                src = src.split('?')[0];
                            }
                            image_urls.push(src);
                            const placeholder = document.createTextNode(`{{IMG_${i}}}`);
                            img.parentNode.replaceChild(placeholder, img);
                        }
                    });

                    let markdown = contentEl.innerText.replace(/\\n{3,}/g, '\\n\\n').trim();
                    return { title, author, content: markdown, image_urls };
                }
            """)
        elif platform_id == 'x':
            # X 的逻辑：尝试抓取主推文内容或长文内容
            return await page.evaluate("""
                () => {
                    // 1. 查找推文或长文容器
                    const tweet = document.querySelector('article[data-testid="tweet"]') ||
                                  document.querySelector('article[role="article"]') ||
                                  document.querySelector('main article');
                    if (!tweet) return null;

                    // 2. 提取作者
                    const authorEl = document.querySelector('div[data-testid="User-Name"]') ||
                                     document.querySelector('div[data-testid="AuthorInfo-name"]');
                    const author = authorEl?.innerText?.split('\\n')[0] || 'X_User';

                    // 3. 提取内容（支持普通推文和长文）
                    const textEl = tweet.querySelector('div[data-testid="tweetText"]') ||
                                   tweet.querySelector('div[data-testid="articleBody"]') ||
                                   tweet;

                    // 4. 提取标题
                    let title = '';
                    const articleTitleEl = tweet.querySelector('div[data-testid="articleTitle"]');
                    if (articleTitleEl) {
                        title = articleTitleEl.innerText;
                    } else {
                        // 如果没有专门的标题，使用内容前30个字符
                        const text = textEl?.innerText || '';
                        title = text.slice(0, 30).replace(/\\n/g, ' ') || 'X_Post';
                    }

                    // 5. 提取图片
                    const image_urls = [];
                    // 查找所有可能的图片容器
                    const photoEls = tweet.querySelectorAll('div[data-testid="tweetPhoto"] img, div[data-testid="articleImage"] img, img[src*="/media/"], img[src*="pbs.twimg.com/media"]');

                    photoEls.forEach((img, i) => {
                        let src = img.getAttribute('src');
                        if (src) {
                            // 转换为原图链接
                            if (src.includes('format=')) {
                                // 处理类似 https://pbs.twimg.com/media/xxxx?format=jpg&name=small 的链接
                                src = src.replace(/name=[a-zA-Z0-9_]+/, 'name=large');
                            } else if (src.includes('pbs.twimg.com/media')) {
                                // 如果没有 name 参数，追加
                                if (!src.includes('name=')) {
                                    src += '&name=large';
                                }
                            }

                            // 避免重复添加
                            if (!image_urls.includes(src)) {
                                image_urls.push(src);
                                // 尝试替换 DOM 中的图片为占位符（仅对可见图片）
                                try {
                                    const placeholder = document.createTextNode(`{{IMG_${image_urls.length - 1}}}`);
                                    if (img.parentNode) {
                                        img.parentNode.replaceChild(placeholder, img);
                                    }
                                } catch (e) {}
                            }
                        }
                    });

                    let markdown = textEl?.innerText || '';
                    return { title, author, content: markdown, image_urls };
                }
            """)
        return None

    async def download_images(self, page, urls, platform_id):
        downloaded = []
        import tempfile
        temp_dir = Path(tempfile.gettempdir()) / "article_saver_images"
        temp_dir.mkdir(parents=True, exist_ok=True)

        for i, url in enumerate(urls):
            try:
                self.log(f"  ⬇️ 下载图片 [{i+1}/{len(urls)}]: {url[:50]}...")

                # 在浏览器环境下下载以获取原图（处理 referer/cookies）
                img_data = await page.evaluate("""
                    async (url) => {
                        try {
                            const response = await fetch(url);
                            const blob = await response.blob();
                            return await new Promise((resolve, reject) => {
                                const reader = new FileReader();
                                reader.onloadend = () => {
                                    const base64data = reader.result.split(',')[1];
                                    resolve({ success: true, data: base64data, type: blob.type });
                                };
                                reader.onerror = reject;
                                reader.readAsDataURL(blob);
                            });
                        } catch (e) {
                            return { success: false, error: e.toString() };
                        }
                    }
                """, url)

                if img_data and img_data.get('success'):
                    import base64
                    content_type = img_data.get('type', 'image/jpeg')
                    ext = '.jpg'
                    if 'png' in content_type: ext = '.png'
                    elif 'gif' in content_type: ext = '.gif'
                    elif 'webp' in content_type: ext = '.webp'

                    filename = f"img_{i:02d}{ext}"
                    filepath = temp_dir / filename
                    filepath.write_bytes(base64.b64decode(img_data['data']))

                    downloaded.append({
                        "index": i,
                        "filename": filename,
                        "temp_path": str(filepath)
                    })
            except Exception as e:
                self.log(f"  ❌ 下载失败: {str(e)}")

        return downloaded

    def save(self, scrape_result, url):
        data = scrape_result['data']
        platform_name = scrape_result['platform_name']

        # 路径规划: {ROOT}/{Platform}/{Date}_{Title}/
        date_str = datetime.now().strftime("%Y-%m-%d")
        title = self.sanitize_filename(data['title'])
        folder_name = f"{date_str}_{title}"

        save_dir = self.output_root / platform_name / folder_name
        save_dir.mkdir(parents=True, exist_ok=True)

        # 移动图片
        for img_info in data['downloaded_images']:
            src = Path(img_info['temp_path'])
            dst = save_dir / img_info['filename']
            if src.exists():
                shutil.move(str(src), str(dst))

        # 处理 Markdown 中的图片引用
        content = data['content']
        for img_info in data['downloaded_images']:
            placeholder = f"{{{{IMG_{img_info['index']}}}}}"
            content = content.replace(placeholder, f"\n![图片]({img_info['filename']})\n")

        # 写入文件
        meta = f"""---
title: {data['title']}
author: {data['author']}
platform: {platform_name}
url: {url}
saved_at: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
---

"""
        md_file = save_dir / "content.md"
        md_file.write_text(meta + content, encoding='utf-8')

        self.log(f"\n✅ 已保存至: {save_dir}")
        return str(save_dir)

async def main():
    if len(sys.argv) < 2:
        print("Usage: python saver.py <url>")
        return

    url = sys.argv[1]
    saver = ArticleSaver()
    result = await saver.scrape(url)

    if result.get('success'):
        saver.save(result, url)
    else:
        print(f"❌ 抓取失败: {result.get('error')}")

if __name__ == "__main__":
    asyncio.run(main())
