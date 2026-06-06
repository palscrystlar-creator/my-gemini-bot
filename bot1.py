import os
import asyncio
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web
from groq import Groq

# Sozlamalar
BOT_TOKEN = "8799568905:AAGY-PYkbve9LkNp2Fy922FAibTopmomu5s"
GROQ_API_KEY = "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"
WEBHOOK_URL = "https://my-gemini-bot-1-14qh.onrender.com"
PORT = int(os.environ.get("PORT", 8080))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
ai_client = Groq(api_key=GROQ_API_KEY)
user_histories = {} 

class IELTSMockState(StatesGroup):
    part1_q1 = State()
    part2_cue = State()
    part3_q1 = State()

# --- 1. START HANDLER ---
@dp.message(CommandStart())
async def start_command(message: types.Message):
    await message.answer("<b>Salom!</b> Men ShavkatoV AI botiman.\n\n"
                         "🏆 /mock_ielts - IELTS imtihonini boshlash\n"
                         "💬 Yoki shunchaki matn yozing - suhbatlashamiz.", parse_mode="HTML")

# --- 2. IELTS MOCK HANDLER (Boshlanishi) ---
@dp.message(Command("mock_ielts"))
async def start_ielts_mock(message: types.Message, state: FSMContext):
    await message.answer("🎬 <b>IELTS Speaking Mock boshlandi!</b>\nPart 1 savoli: Where are you from?", parse_mode="HTML")
    await state.set_state(IELTSMockState.part1_q1)

@dp.message(IELTSMockState.part1_q1)
async def p1_handler(message: types.Message, state: FSMContext):
    await message.answer("✅ Part 1 qabul qilindi. Endi Part 2 (Cue Card) savoli...")
    await state.set_state(IELTSMockState.part2_cue)

# --- 3. ODDIY CHAT HANDLER (Oxirgi o'rinda) ---
@dp.message(F.text & ~F.text.startswith("/"))
async def chat_with_ai(message: types.Message):
    user_id = message.from_user.id
    if user_id not in user_histories:
        user_histories[user_id] = [{"role": "system", "content": "Siz ShavkatoV AI siz."}]
    
    user_histories[user_id].append({"role": "user", "content": message.text})
    
    # Tarixni limitlash
    if len(user_histories[user_id]) > 10: 
        user_histories[user_id] = [user_histories[user_id][0]] + user_histories[user_id][-9:]

    chat_completion = ai_client.chat.completions.create(messages=user_histories[user_id], model="llama-3.3-70b-versatile")
    ai_response = chat_completion.choices[0].message.content
    
    user_histories[user_id].append({"role": "assistant", "content": ai_response})
    await message.answer(ai_response)

# --- Server qismi ---
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
