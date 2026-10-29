# Abest eSIM Luck Wheel Bot

بوت يولد إيميلات مؤقتة من mail.tm ويدور عجلة الحظ على abestesim.com لحد ما يجي Free eSIM، ويبعتلك النتيجة على تيليجرام.

## الملفات

- `bot.py` — السكربت الرئيسي
- `Dockerfile` — جاهز لـ Railway
- `requirements.txt`
- `.env.example` — مثال للمتغيرات

## النشر على Railway

1. ارفع المشروع على GitHub
2. ادخل [railway.app](https://railway.app) → New Project → Deploy from GitHub
3. اختار الريبو
4. أضف المتغيرات دي في Variables:

```
TELEGRAM_BOT_TOKEN=xxxx:yyyy
TELEGRAM_CHAT_ID=123456789
MAX_ATTEMPTS=30
```

5. اضغط Deploy

## ملاحظات

- البوت شغال headless (مناسب للسيرفر)
- الـ Captcha ممكن يوقف الأتمتة أحيانًا
- Free eSIM نادر، فممكن يحتاج محاولات كتير
