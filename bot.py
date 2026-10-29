#!/usr/bin/env python3
"""
Abest eSIM Luck Wheel Bot
Telegram Bot with /start and /stop
"""

import asyncio
import os
import random
import string
import httpx
from playwright.async_api import async_playwright
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

load_dotenv()

# ============ Settings ============
TARGET_URL = "https://abestesim.com/products/esim-egypt?rs_ref=XDUxWVAd"
MAX_ATTEMPTS = int(os.getenv("MAX_ATTEMPTS", "50"))
DELAY_BETWEEN = (5, 10)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
# ==================================

MAILTM_API = "https://api.mail.tm"

# Bot state
is_running = False
current_task = None


def random_string(length=12):
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))


async def create_mailtm_account(retries=3):
    """Create a temporary email on mail.tm with retries"""
    for attempt in range(retries):
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.get(f"{MAILTM_API}/domains")
                r.raise_for_status()
                domains = r.json().get("hydra:member", [])
                if not domains:
                    raise Exception("No domains from mail.tm")

                domain = domains[0]["domain"]
                address = f"{random_string()}@{domain}"
                password = random_string(16)

                r = await client.post(
                    f"{MAILTM_API}/accounts",
                    json={"address": address, "password": password},
                )
                if r.status_code not in (200, 201):
                    raise Exception(f"Create failed: {r.text[:100]}")

                r = await client.post(
                    f"{MAILTM_API}/token",
                    json={"address": address, "password": password},
                )
                r.raise_for_status()
                return address
        except Exception as e:
            if attempt == retries - 1:
                raise e
            await asyncio.sleep(2)
    raise Exception("Failed to create mail.tm account")


async def spin_once(page, email: str) -> str:
    """Submit email and try to spin the wheel"""
    try:
        await page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(2000)

        email_input = page.locator("#email")
        await email_input.wait_for(state="visible", timeout=15000)
        await email_input.fill(email)
        await page.wait_for_timeout(600)

        btn = page.get_by_role("button", name="Continue to the wheel")
        if await btn.count() == 0:
            btn = page.locator("button:has-text('Continue')")
        await btn.first.click()
        await page.wait_for_timeout(4000)

        for sel in [
            "button:has-text('Spin')",
            "button:has-text('SPIN')",
            "button:has-text('Turn')",
            "[class*='spin']",
        ]:
            locator = page.locator(sel)
            if await locator.count() > 0:
                await locator.first.click()
                await page.wait_for_timeout(7000)
                break

        text = (await page.inner_text("body")).lower()

        if "free esim" in text:
            return "Free eSIM 🎉"
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
        return f"failed ({str(e)[:40]})"


async def run_wheel_loop(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Main spinning loop - can be cancelled by /stop"""
    global is_running

    await context.bot.send_message(
        chat_id=chat_id,
        text="🚀 <b>البوت بدأ الشغل</b>\nجاري توليد إيميلات ودوران العجلة...\n\nاكتب /stop لإيقافه",
        parse_mode="HTML",
    )

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-blink-features=AutomationControlled",
            ],
        )

        try:
            for attempt in range(1, MAX_ATTEMPTS + 1):
                if not is_running:
                    break

                # Fresh context every attempt
                browser_context = await browser.new_context(
                    viewport={"width": 1280, "height": 900},
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                    locale="en-US",
                )
                page = await browser_context.new_page()

                try:
                    email = await create_mailtm_account()
                    result = await spin_once(page, email)

                    msg = (
                        f"🎯 <b>محاولة #{attempt}</b>\n"
                        f"📧 <code>{email}</code>\n"
                        f"🎁 النتيجة: <b>{result}</b>"
                    )
                    await context.bot.send_message(
                        chat_id=chat_id, text=msg, parse_mode="HTML"
                    )

                    if "Free eSIM" in result:
                        await context.bot.send_message(
                            chat_id=chat_id,
                            text=(
                                f"🎉🎉🎉 <b>فزنا بـ Free eSIM !!</b>\n\n"
                                f"📧 الإيميل: <code>{email}</code>\n"
                                f"🔗 {TARGET_URL}"
                            ),
                            parse_mode="HTML",
                        )
                        is_running = False
                        break

                except Exception as e:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=f"⚠️ خطأ في المحاولة #{attempt}:\n<code>{str(e)[:150]}</code>",
                        parse_mode="HTML",
                    )
                finally:
                    await page.close()
                    await browser_context.close()

                if not is_running:
                    break

                delay = random.uniform(*DELAY_BETWEEN)
                await asyncio.sleep(delay)

        finally:
            await browser.close()

    is_running = False
    await context.bot.send_message(
        chat_id=chat_id,
        text="🛑 <b>البوت توقف</b>",
        parse_mode="HTML",
    )


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global is_running, current_task

    if is_running:
        await update.message.reply_text("البوت شغال بالفعل 🔄\nاكتب /stop عشان توقفه")
        return

    is_running = True
    chat_id = update.effective_chat.id
    current_task = asyncio.create_task(run_wheel_loop(chat_id, context))


async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global is_running, current_task

    if not is_running:
        await update.message.reply_text("البوت مش شغال أصلاً 😴")
        return

    is_running = False
    await update.message.reply_text("⏹ جاري إيقاف البوت...")

    if current_task and not current_task.done():
        current_task.cancel()
        try:
            await current_task
        except asyncio.CancelledError:
            pass


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 <b>أوامر البوت:</b>\n\n"
        "/start - بدء دوران العجلة\n"
        "/stop - إيقاف البوت\n"
        "/help - عرض المساعدة",
        parse_mode="HTML",
    )


def main():
    if not TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN is missing!")
        return

    print("🤖 Starting Telegram bot...")
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("stop", stop_command))
    app.add_handler(CommandHandler("help", help_command))

    print("✅ Bot is running. Waiting for /start and /stop ...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
