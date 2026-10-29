# Abest eSIM Luck Wheel Bot

بوت تيليجرام يدور عجلة الحظ على abestesim.com باستخدام إيميلات mail.tm.

## الأوامر

- `/start` → يبدأ الدوران
- `/stop`  → يوقف البوت فوراً
- `/help`  → المساعدة

## المتغيرات المطلوبة (Railway Variables)

```
TELEGRAM_BOT_TOKEN=xxxx:yyyy
MAX_ATTEMPTS=50
```

> ملاحظة: مفيش حاجة لـ TELEGRAM_CHAT_ID دلوقتي لأن البوت بيرد على اللي بيكتب الأمر.

## النشر على Railway

1. ارفع الكود على GitHub
2. New Project → Deploy from GitHub
3. حط `TELEGRAM_BOT_TOKEN` في Variables
4. Deploy

البوت هيشتغل ويستنى أوامر `/start` و `/stop`.
