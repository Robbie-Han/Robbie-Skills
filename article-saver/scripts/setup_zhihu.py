
import asyncio
from playwright.async_api import async_playwright
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
ZHIHU_AUTH_FILE = DATA_DIR / "zhihu_auth.json"

async def setup_zhihu():
    print("🤖 正在启动浏览器...")
    print("👉 请在打开的浏览器中扫描二维码或输入账号密码登录知乎")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        await page.goto("https://www.zhihu.com/signin")

        # 等待用户手动登录，直到跳转到首页
        try:
            await page.wait_for_url("https://www.zhihu.com/", timeout=0)
            print("✅ 检测到登录成功！")

            # 保存登录态
            await context.storage_state(path=ZHIHU_AUTH_FILE)
            print(f"💾 登录态已保存至: {ZHIHU_AUTH_FILE}")

        except Exception as e:
            print(f"❌ 发生错误: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(setup_zhihu())
