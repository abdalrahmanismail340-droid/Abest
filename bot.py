#!/usr/bin/env python3
"""
Abest eSIM Luck Wheel Bot
- Generates temp emails via mail.tm
- Spins the luck wheel on abestesim.com
- Sends results to Telegram
- Ready for Railway deployment
"""

import asyncio
import os
import random
import string
import httpx
from playwright.async_api import async_playwright
from dotenv import load_dotenv

load_dotenv()

# ============ Settings ============
TARGET_URL = "https://abestesim.com/products/esim-egypt?rs_ref=XDUxWVAd"
MAX_ATTEMPTS = int(os.getenv("MAX_ATTEMPTS", "30"))
DELAY_BETWEEN = (6, 12)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
# ==================================

MAILTM_API = "https://api.mail.tm"


def random_string(length=12):
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))


async def send_telegram(text: str):
    """Send a message to Telegram"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            await client.post(
                url,
                json={
                    "chat_id": TELEGRAM_CHAT_ID,
                    "text": text,
                    "parse_mode": "HTML",
                },
            )
        except Exception as e:
            print(f"Telegram send failed: {e}")


async def create_mailtm_account():
    """Create a temporary email account on mail.tm"""
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(f"{MAILTM_API}/domains")
        r.raise_for_status()
        domains = r.json().get("hydra:member", [])
        if not domains:
            raise Exception("No domains available from mail.tm")

        domain = domains[0]["domain"]
        address = f"{random_string()}@{domain}"
        password = random_string(16)

        r = await client.post(
            f"{MAILTM_API}/accounts",
            json={"address": address, "password": password},
        )
        if r.status_code not in (200, 201):
            raise Exception(f"Failed to create account: {r.text}")

        r = await client.post(
            f"{MAILTM_API}/token",
            json={"address": address, "password": password},
        )
        r.raise_for_status()
        token = r.json()["token"]

        return address, token


async def spin_once(page, email: str) -> str:
    """Submit email and spin the wheel. Returns the prize result."""
    try:
        await page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(2500)

        email_input = page.locator("#email")
        await email_input.wait_for(state="visible", timeout=20000)
        await email_input.fill(email)
        await page.wait_for_timeout(700)

        btn = page.get_by_role("button", name="Continue to the wheel")
        await btn.click()
        await page.wait_for_timeout(4500)

        # Try to click Spin button if it appears
        for sel in [
            "button:has-text('Spin')",
            "button:has-text('SPIN')",
            "[class*='spin']",
            "button:has-text('Turn')",
        ]:
            if await page.locator(sel).count() > 0:
                await page.locator(sel).first.click()
                await page.wait_for_timeout(7500)
                break

        text = (await page.inner_text("body")).lower()

        if "free esim" in text:
            return "Free eSIM"
        if "10% off" in text:
            return "10% OFF"
        if "12% off" in text:
            return "12% OFF"
        if "11% off" in text:
            return "11% OFF"
        if "sorry" in text:
            return "Sorry"
        return "unknown"

    except Exception as e:
        print(f"  [Error] {e}")
        return "failed"


async def main():
    print("🚀 Starting Abest Wheel Bot...")
    await send_telegram("🚀 <b>Abest Wheel Bot بدأ الشغل</b>\nجاري توليد إيميلات ودوران العجلة...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ],
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        page = await context.new_page()

        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                email, token = await create_mailtm_account()
                print(f"\n[{attempt}/{MAX_ATTEMPTS}] Trying: {email}")

                result = await spin_once(page, email)
                print(f"  → Result: {result}")

                msg = f"🎯 <b>محاولة #{attempt}</b>\n📧 <code>{email}</code>\n🎁 النتيجة: <b>{result}</b>"
                await send_telegram(msg)

                if result == "Free eSIM":
                    win_msg = (
                        f"🎉🎉🎉 <b>فزنا بـ Free eSIM !!</b>\n\n"
                        f"📧 الإيميل: <code>{email}</code>\n"
                        f"🔗 الرابط: {TARGET_URL}"
                    )
                    await send_telegram(win_msg)
                    print("\n" + "=" * 50)
                    print("🎉 FREE eSIM WON!")
                    print(f"Email: {email}")
                    print("=" * 50)
                    break

            except Exception as e:
                print(f"  [Attempt Error] {e}")
                await send_telegram(f"⚠️ خطأ في المحاولة #{attempt}: {str(e)[:200]}")

            delay = random.uniform(*DELAY_BETWEEN)
            print(f"  → Waiting {delay:.1f}s...")
            await asyncio.sleep(delay)

        await browser.close()
        await send_telegram("✅ البوت خلص الشغل")


if __name__ == "__main__":
    asyncio.run(main())
