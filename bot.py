import asyncio
import os
import requests
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram import F
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
CHANNEL_ID = "@bot_pro_bot_you"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

async def is_subscribed(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

def safe_get(url, params=None):
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        return data if isinstance(data, list) else []
    except Exception as e:
        print(f"CoinGecko error: {e}")
        return []

def get_top10():
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": 10,
        "page": 1,
        "price_change_percentage": "24h"
    }
    return safe_get(url, params)

def get_gainers_losers():
    url = "https://api.coingecko.com/api/v3/coins/markets"
    p = {"vs_currency": "usd", "per_page": 10, "page": 1}
    gainers = safe_get(url, {**p, "order": "percent_change_24h_desc"})
    losers  = safe_get(url, {**p, "order": "percent_change_24h_asc"})
    return gainers[:10], losers[:10]

def format_top_message():
    data = get_top10()
    if not data:
        return "⚠️ Временные проблемы с CoinGecko. Попробуй через 30–60 секунд."

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
    if not await is_subscribed(message.from_user.id):
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Подписаться на канал", url="https://t.me/bot_pro_bot_you")],
            [InlineKeyboardButton(text="Я подписался ✅", callback_data="check_sub")]
        ])
        await message.answer(
            "👋 Чтобы пользоваться ботом — подпишись на наш канал!\n\n"
            "🔗 https://t.me/bot_pro_bot_you",
            reply_markup=kb
        )
        return

    await message.answer(format_top_message(), reply_markup=main_keyboard())

@dp.callback_query(F.data == "check_sub")
async def check_sub(callback: types.CallbackQuery):
    if await is_subscribed(callback.from_user.id):
        await callback.message.edit_text(format_top_message(), reply_markup=main_keyboard())
        await callback.answer("✅ Подписка подтверждена!")
    else:
        await callback.answer("❌ Ты ещё не подписался", show_alert=True)

@dp.callback_query(F.data.in_(["courses", "changes", "forecast"]))
async def protected_handler(callback: types.CallbackQuery):
    if not await is_subscribed(callback.from_user.id):
        await callback.answer("❌ Сначала подпишись на канал!", show_alert=True)
        return

    if callback.data == "courses":
        data = get_top10()
        text = "Курсы топ-10:\n\n"
        for i, coin in enumerate(data, 1):
            symbol = coin['symbol'].upper()
            price = f"${coin['current_price']:,.0f}" if coin['current_price'] > 10 else f"${coin['current_price']:.4f}"
            change = coin.get('price_change_percentage_24h', 0)
            text += f"{i}. {symbol} — {price}   {change:+.1f}%\n"
        await callback.message.edit_text(text, reply_markup=main_keyboard())

    elif callback.data == "changes":
        gainers, losers = get_gainers_losers()
        text = "Изменения за 24ч\n\nГейнеры 🔥\n"
        for c in gainers:
            text += f"{c['symbol'].upper()}  {c.get('price_change_percentage_24h', 0):+.1f}%\n"
        text += "\nЛузеры 📉\n"
        for c in losers:
            text += f"{c['symbol'].upper()}  {c.get('price_change_percentage_24h', 0):+.1f}%\n"
        await callback.message.edit_text(text, reply_markup=main_keyboard())

    elif callback.data == "forecast":
        if not GROQ_API_KEY:
            ai_text = "❌ GROQ_API_KEY не найден"
        else:
            try:
                r = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {GROQ_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "llama-3.1-8b-instant",          # ← новая модель (быстрая и бесплатная)
                        "messages": [{"role": "user", "content": "Ты крипто-аналитик. Дай короткий честный прогноз по рынку на 24–48 часов: топ гейнеры, риски, общее настроение. Не больше 150 слов."}],
                        "max_tokens": 300,
                        "temperature": 0.7
                    },
                    timeout=12
                )
                if r.status_code == 200:
                    ai_text = r.json()["choices"][0]["message"]["content"]
                else:
                    ai_text = f"Groq ошибка {r.status_code}: {r.text[:300]}"
            except Exception as e:
                ai_text = f"Ошибка: {type(e).__name__}\n{str(e)[:200]}"

        await callback.message.edit_text(f"Прогноз на сегодня:\n\n{ai_text}", reply_markup=main_keyboard())

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
