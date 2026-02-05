import asyncio
import os
import requests
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram import F
from dotenv import load_dotenv

load_dotenv()  # для локального запуска

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

def get_top10():
    url = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=10&page=1&price_change_percentage=24h"
    return requests.get(url, timeout=10).json()

def get_gainers_losers():
    url = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=percent_change_24h_desc&per_page=10&page=1"
    gainers = requests.get(url, timeout=10).json()
    losers = requests.get(url.replace("desc", "asc"), timeout=10).json()
    return gainers[:10], losers[:10]

def format_top_message():
    data = get_top10()
    text = "Привет! Вот что на рынке прямо сейчас\n\nТоп-10 по капитализации:\n"
    max_change = max(data, key=lambda x: abs(x.get('price_change_percentage_24h', 0)))

    for i, coin in enumerate(data, 1):
        symbol = coin['symbol'].upper()
        price = f"${coin['current_price']:,.0f}" if coin['current_price'] > 10 else f"${coin['current_price']:.4f}"
        change = coin.get('price_change_percentage_24h', 0)
        arrow = "🔥" if change > 5 else "📉" if change < -5 else ""
        text += f"{i}. {symbol} — {price}   {change:+.1f}% {arrow}\n"

    text += f"\nОбратить внимание: {max_change['symbol'].upper()} изменился на {max_change.get('price_change_percentage_24h', 0):+.1f}% — самое большое движение!"
    return text

def main_keyboard():
    kb = [
        [InlineKeyboardButton(text="Курсы", callback_data="courses"),
         InlineKeyboardButton(text="Изменения", callback_data="changes")],
        [InlineKeyboardButton(text="Прогноз", callback_data="forecast")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

@dp.message(Command("start"))
async def start(message: types.Message):
    text = format_top_message()
    await message.answer(text, reply_markup=main_keyboard())

@dp.callback_query(F.data == "courses")
async def show_courses(callback: types.CallbackQuery):
    data = get_top10()
    text = "Курсы топ-10:\n\n"
    for i, coin in enumerate(data, 1):
        symbol = coin['symbol'].upper()
        price = f"${coin['current_price']:,.0f}" if coin['current_price'] > 10 else f"${coin['current_price']:.4f}"
        change = coin.get('price_change_percentage_24h', 0)
        text += f"{i}. {symbol} — {price}   {change:+.1f}%\n"
    await callback.message.edit_text(text, reply_markup=main_keyboard())

@dp.callback_query(F.data == "changes")
async def show_changes(callback: types.CallbackQuery):
    gainers, losers = get_gainers_losers()
    text = "Изменения за 24ч\n\nГейнеры 🔥\n"
    for coin in gainers:
        text += f"{coin['symbol'].upper()}  {coin.get('price_change_percentage_24h', 0):+.1f}%\n"
    text += "\nЛузеры 📉\n"
    for coin in losers:
        text += f"{coin['symbol'].upper()}  {coin.get('price_change_percentage_24h', 0):+.1f}%\n"
    await callback.message.edit_text(text, reply_markup=main_keyboard())

@dp.callback_query(F.data == "forecast")
async def show_forecast(callback: types.CallbackQuery):
    if GROQ_API_KEY:
        try:
            r = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "llama3-8b-8192",
                    "messages": [{"role": "user", "content": "Ты крипто-аналитик. Дай короткий честный прогноз по рынку на 24–48 часов: топ гейнеры, риски, общее настроение. Не больше 150 слов."}],
                    "max_tokens": 300,
                    "temperature": 0.7
                },
                timeout=15
            )
            ai_text = r.json()["choices"][0]["message"]["content"]
        except:
            ai_text = "Не удалось подключиться к ИИ. Попробуй позже."
    else:
        ai_text = "Добавь переменную GROQ_API_KEY для настоящего ИИ-прогноза от Groq (бесплатно)."
    
    text = f"Прогноз на сегодня:\n\n{ai_text}"
    await callback.message.edit_text(text, reply_markup=main_keyboard())

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
