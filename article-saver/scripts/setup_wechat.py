import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

DATA_DIR = Path(__file__).parent.parent / "data"
WECHAT_AUTH_FILE = DATA_DIR / "wechat_auth.json"

async def setup_wechat(wait_seconds: int = 120):
    print("🤖 正在启动浏览器...")
    print("👉 请在打开的浏览器中扫描二维码或输入账号密码登录微信公众号平台")
    
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        # 打开微信文章页面（任意一个）
        await page.goto("https://mp.weixin.qq.com/")

        print("\n请在浏览器中完成以下操作：")
        print("1. 点击右上角「登录」")
        print("2. 使用微信扫码登录")
        print(f"3. 登录成功后会自动保存（最多等待 {wait_seconds} 秒）")
        print("\n等待登录中...")

        # 等待登录成功（检测页面变化）
        try:
            # 等待登录成功后的元素出现
            await page.wait_for_selector(".weui-desktop-account__nickname", timeout=wait_seconds * 1000)
            print("✅ 检测到登录成功！")
        except Exception as e:
            # 超时后也保存，可能用户已经登录
            print(f"⚠️ 等待超时或发生错误，尝试保存当前状态... {e}")

        # 保存认证状态
        storage = await context.storage_state()
        
        with open(WECHAT_AUTH_FILE, 'w', encoding='utf-8') as f:
            json.dump(storage, f, ensure_ascii=False, indent=2)

        print(f"💾 登录态已保存至: {WECHAT_AUTH_FILE}")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(setup_wechat())
