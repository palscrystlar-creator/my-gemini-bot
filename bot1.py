import os
import uuid
import random
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web
from groq import Groq
import edge_tts
from aiogram.types import FSInputFile

# --- SOZLAMALAR ---
BOT_TOKEN = "8799568905:AAGY-PYkbve9LkNp2Fy922FAibTopmomu5s"
GROQ_API_KEY = "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"
WEBHOOK_URL = "https://my-gemini-bot-1-14qh.onrender.com"
PORT = int(os.environ.get("PORT", 8080))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
ai_client = Groq(api_key=GROQ_API_KEY)

QUESTIONS = {
    "part1": ["Where are you from?", "Do you work or are you a student?", "What do you like about your city?", "Do you have any hobbies?"],
    "part2": ["Describe a book you enjoyed reading.", "Describe a person who influenced you.", "Describe a place you visited."],
    "part3": ["Why do people read books?", "How does influence shape a person?", "Is tourism important for your country?"]
}

class IELTSState(StatesGroup):
    part1 = State()
    part2 = State()
    part3 = State()

async def send_voice_response(message, text, voice="en-US-BrianNeural"):
    path = f"voice_{uuid.uuid4().hex}.mp3"
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(path)
    await message.answer_voice(FSInputFile(path), caption=f"🗣 Examiner: {text}")
    os.remove(path)

# --- HANDLERLAR ---

@dp.message(CommandStart())
async def start_command(message: types.Message, state: FSMContext):
    await state.clear() # ESKI HOLATNI TOZALASH
    await message.answer("Salom! /mock_ielts orqali imtihonni boshlang.")

@dp.message(Command("mock_ielts"))
async def start_mock(message: types.Message, state: FSMContext):
    await state.clear() # ESKI HOLATNI TOZALASH
    q = random.choice(QUESTIONS["part1"])
    await send_voice_response(message, f"Part 1. {q}")
    await state.set_state(IELTSState.part1)

@dp.message(IELTSState.part1, F.voice)
async def p1_handler(message: types.Message, state: FSMContext):
    q = random.choice(QUESTIONS["part2"])
    await send_voice_response(message, f"Part 2. {q}")
    await state.set_state(IELTSState.part2)

@dp.message(IELTSState.part2, F.voice)
async def p2_handler(message: types.Message, state: FSMContext):
    q = random.choice(QUESTIONS["part3"])
    await send_voice_response(message, f"Part 3. {q}")
    await state.set_state(IELTSState.part3)

@dp.message(IELTSState.part3, F.voice)
async def p3_handler(message: types.Message, state: FSMContext):
    await message.answer("Test finished! Result: Band 7.0.")
    await state.clear() # TEST TUGADI

@dp.message(F.text & ~F.text.startswith("/"))
async def chat_with_ai(message: types.Message, state: FSMContext):
    if await state.get_state(): return 
    completion = ai_client.chat.completions.create(
        messages=[{"role": "user", "content": message.text}],
        model="llama-3.3-70b-versatile"
    )
    await message.answer(completion.choices[0].message.content)

# --- SERVER ---
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
