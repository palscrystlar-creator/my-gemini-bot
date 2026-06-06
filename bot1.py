import os
import asyncio
import uuid
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web
from groq import Groq
import edge_tts

# Sozlamalar
BOT_TOKEN = "8799568905:AAGY-PYkbve9LkNp2Fy922FAibTopmomu5s"
GROQ_API_KEY = "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"
WEBHOOK_URL = "https://my-gemini-bot-1-14qh.onrender.com"
PORT = int(os.environ.get("PORT", 8080))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
ai_client = Groq(api_key=GROQ_API_KEY)
user_histories = {} # Oddiy chat uchun xotira

# --- Baza funksiyalari ---
def init_db():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, name TEXT, last_score REAL)')
    conn.commit()
    conn.close()

init_db()

# --- Handlerlar ---
@dp.message(CommandStart())
async def start_command(message: types.Message):
    welcome_text = (f"<b>Salom, {message.from_user.full_name}!</b> 👋\n\n"
                    "Men ShavkatoV AI botiman. /mock_ielts orqali imtihonni boshlashingiz mumkin.")
    await message.answer(welcome_text, parse_mode="HTML")

@dp.message(F.text & ~F.text.startswith("/"))
async def chat_with_ai(message: types.Message):
    user_id = message.from_user.id
    if user_id not in user_histories:
        user_histories[user_id] = [{"role": "system", "content": "Siz ShavkatoV AI siz."}]
    
    user_histories[user_id].append({"role": "user", "content": message.text})
    
    # Tarixni limitlash
    if len(user_histories[user_id]) > 10: user_histories[user_id] = [user_histories[user_id][0]] + user_histories[user_id][-9:]

    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    chat_completion = ai_client.chat.completions.create(messages=user_histories[user_id], model="llama-3.3-70b-versatile")
    ai_response = chat_completion.choices[0].message.content
    
    user_histories[user_id].append({"role": "assistant", "content": ai_response})
    await message.answer(ai_response)

# --- Webhook va Server ---
async def handle_webhook(request):
    data = await request.json()
    await dp.feed_update(bot, types.Update(**data))
    return web.Response(text="OK")

async def on_startup(app):
    await bot.set_webhook(f"{WEBHOOK_URL}/webhook")

def main():
    app = web.Application()
    app.router.add_post("/webhook", handle_webhook)
    app.on_startup.append(on_startup)
    web.run_app(app, host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    main()
