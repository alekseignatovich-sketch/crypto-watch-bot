# Crypto Watch AI

Простой Telegram-бот для крипты: открываешь — сразу сводка + 3 кнопки.

## Запуск локально
1. `pip install -r requirements.txt`
2. Создай `.env` (скопируй из .env.example)
3. `python bot.py`

## Деплой на Railway
1. Создай репозиторий на GitHub и закинь все файлы
2. Зайди на railway.app → New Project → Deploy from GitHub
3. Добавь переменные окружения:
   - BOT_TOKEN
   - GROQ_API_KEY (опционально, бесплатно на groq.com)
4. Deploy → готово!
