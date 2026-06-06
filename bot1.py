import os
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web
from groq import Groq
import edge_tts
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# --- SOZLAMALAR ---
BOT_TOKEN = "8799568905:AAGY-PYkbve9LkNp2Fy922FAibTopmomu5s"
GROQ_API_KEY = "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"
WEBHOOK_URL = "https://my-gemini-bot-1-14qh.onrender.com"
PORT = int(os.environ.get("PORT", 8080))
USERS_FILE = "users.txt"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
ai_client = Groq(api_key=GROQ_API_KEY)

class IELTSMockState(StatesGroup):
    part1_q1 = State()
    part1_q2 = State()
    part1_q3 = State()
    part2_cue = State()
    part3_q1 = State()
    part3_q2 = State()
    part3_q3 = State()

EXAMINER_PROMPT = "You are a strict IELTS examiner. Ask only ONE question at a time. No filler."

# --- YORDAMCHI FUNKSIYALAR ---
def save_user(user_id):
    if not os.path.exists(USERS_FILE): open(USERS_FILE, 'w').close()
    with open(USERS_FILE, "r") as f: users = f.read().splitlines()
    if str(user_id) not in users:
        with open(USERS_FILE, "a") as f: f.write(f"{user_id}\n")

async def transcribe_voice(message: types.Message) -> str:
    file = await bot.get_file(message.voice.file_id)
    path = f"{message.voice.file_id}.ogg"
    await bot.download_file(file.file_path, path)
    with open(path, "rb") as f:
        tr = ai_client.audio.transcriptions.create(file=(path, f.read()), model="whisper-large-v3")
    os.remove(path)
    return tr.text

async def send_examiner_voice(message: types.Message, text: str):
    path = f"examiner_{message.chat.id}.mp3"
    communicate = edge_tts.Communicate(text, "en-US-JennyNeural")
    await communicate.save(path)
    await message.answer_voice(types.FSInputFile(path))
    if os.path.exists(path): os.remove(path)

async def send_daily_challenge():
    if not os.path.exists(USERS_FILE): return
    with open(USERS_FILE, "r") as f: users = set(f.read().splitlines())
    text = "☀️ Daily IELTS Challenge! Topic: Technology. How has technology changed the way we study?"
    for user_id in users:
        try: await bot.send_message(chat_id=user_id, text=text)
        except: continue

# --- HANDLERLAR ---
@dp.message(CommandStart())
async def start_command(message: types.Message):
    save_user(message.chat.id)
    await message.answer("Salom! /mock_ielts yozib imtihonni boshlang.")

@dp.message(Command("mock_ielts"))
async def start_ielts_mock(message: types.Message, state: FSMContext):
    await state.clear()
    completion = ai_client.chat.completions.create(
        messages=[{"role": "system", "content": EXAMINER_PROMPT}, {"role": "user", "content": "Ask a Part 1 question."}],
        model="llama-3.3-70b-versatile",
    )
    q1 = completion.choices[0].message.content
    await message.answer(f"🗣 <b>Part 1:</b>\n{q1}", parse_mode="HTML")
    await send_examiner_voice(message, q1)
    await state.update_data(p1_q1=q1, history=[])
    await state.set_state(IELTSMockState.part1_q1)

@dp.message(IELTSMockState.part1_q1, F.voice)
async def p1_q1_handler(message: types.Message, state: FSMContext):
    text = await transcribe_voice(message)
    data = await state.get_data()
    history = data.get("history", [])
    history.append({"role": "candidate", "content": text})
    completion = ai_client.chat.completions.create(
        messages=[{"role": "system", "content": EXAMINER_PROMPT}, {"role": "user", "content": f"Ask next question based on: {history}"}],
        model="llama-3.3-70b-versatile",
    )
    q2 = completion.choices[0].message.content
    await message.answer(f"🗣 <b>Q2:</b>\n{q2}", parse_mode="HTML")
    await send_examiner_voice(message, q2)
    await state.update_data(history=history)
    await state.set_state(IELTSMockState.part1_q2)

# --- WEBHOOK VA STARTUP ---
async def handle_webhook(request):
    data = await request.json()
    await dp.feed_update(bot, types.Update(**data))
    return web.Response(text="OK")

async def on_startup(app):
    await bot.set_webhook(f"{WEBHOOK_URL}/webhook")

if __name__ == "__main__":
    scheduler = AsyncIOScheduler()
    scheduler.add_job(send_daily_challenge, 'cron', hour=9, minute=0)
    scheduler.start()
    
    app = web.Application()
    app.router.add_post("/webhook", handle_webhook)
    app.on_startup.append(on_startup)
    web.run_app(app, host="0.0.0.0", port=PORT)
