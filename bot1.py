import os
import sqlite3
import uuid
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web
from groq import Groq
import edge_tts
from aiogram.types import FSInputFile

# --- Sozlamalar ---
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

# --- Yordamchi funksiyalar ---
def init_db():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, name TEXT, last_score REAL)')
    conn.commit()
    conn.close()
init_db()

async def transcribe_voice(voice_id):
    file = await bot.get_file(voice_id)
    path = f"{voice_id}.ogg"
    await bot.download_file(file.file_path, path)
    with open(path, "rb") as f:
        transcript = ai_client.audio.transcriptions.create(file=(path, f.read()), model="whisper-large-v3")
    os.remove(path)
    return transcript.text

# --- Handlerlar ---
@dp.message(CommandStart())
async def start_command(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("<b>Salom!</b> Men ShavkatoV AI botiman.\n\n"
                         "🏆 /mock_ielts - IELTS imtihoni\n"
                         "💬 Matn yoki ovoz yuboring - suhbatlashamiz.", parse_mode="HTML")

@dp.message(Command("mock_ielts"))
async def start_ielts_mock(message: types.Message, state: FSMContext):
    await message.answer("🎬 <b>Mock Test boshlandi!</b>\nSavol: Where are you from?", parse_mode="HTML")
    await state.set_state(IELTSMockState.part1_q1)

# Imtihon uchun ovozli handler
@dp.message(IELTSMockState.part1_q1, F.voice)
async def p1_handler(message: types.Message, state: FSMContext):
    text = await transcribe_voice(message.voice.file_id)
    ai_response = "Great! What do you like most about your hometown?"
    
    voice_path = f"mock_{uuid.uuid4().hex}.mp3"
    communicate = edge_tts.Communicate(ai_response, "en-US-BrianNeural")
    await communicate.save(voice_path)
    await message.answer_voice(FSInputFile(voice_path), caption=f"🗣: {ai_response}")
    os.remove(voice_path)

# --- Oddiy Chat (Matn va Ovoz) ---
@dp.message(F.text & ~F.text.startswith("/"))
async def chat_with_ai(message: types.Message, state: FSMContext):
    # Agar imtihon holatida bo'lsa, bu funksiya ishlamaydi
    if await state.get_state() is not None: return

    user_id = message.from_user.id
    if user_id not in user_histories: user_histories[user_id] = [{"role": "system", "content": "Siz ShavkatoV AI siz."}]
    user_histories[user_id].append({"role": "user", "content": message.text})
    
    chat_completion = ai_client.chat.completions.create(messages=user_histories[user_id], model="llama-3.3-70b-versatile")
    ai_response = chat_completion.choices[0].message.content
    
    user_histories[user_id].append({"role": "assistant", "content": ai_response})
    await message.answer(ai_response)

@dp.message(F.voice)
async def handle_voice(message: types.Message, state: FSMContext):
    # Imtihon bo'lmagan paytda oddiy ovozli suhbat
    if await state.get_state() is None:
        await bot.send_chat_action(message.chat.id, "record_voice")
        user_text = await transcribe_voice(message.voice.file_id)
        
        user_id = message.from_user.id
        if user_id not in user_histories: user_histories[user_id] = [{"role": "system", "content": "Siz ShavkatoV AI siz."}]
        user_histories[user_id].append({"role": "user", "content": user_text})
        
        chat_completion = ai_client.chat.completions.create(messages=user_histories[user_id], model="llama-3.3-70b-versatile")
        ai_response = chat_completion.choices[0].message.content
        user_histories[user_id].append({"role": "assistant", "content": ai_response})
        
        voice_path = f"resp_{uuid.uuid4().hex}.mp3"
        communicate = edge_tts.Communicate(ai_response, "uz-UZ-MadinaNeural")
        await communicate.save(voice_path)
        await message.answer_voice(FSInputFile(voice_path), caption=f"✍️ <i>Siz aytdingiz: {user_text}</i>", parse_mode="HTML")
        os.remove(voice_path)

# --- Server ---
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
