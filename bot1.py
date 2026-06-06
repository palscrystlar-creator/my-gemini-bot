import os
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiohttp import web
from groq import Groq
import edge_tts
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# --- SOZLAMALAR ---
BOT_TOKEN = "8799568905:AAGY-PYkbve9LkNp2Fy922FAibTopmomu5s"
GROQ_API_KEY = "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"
WEBHOOK_URL = "https://my-gemini-bot-1-14qh.onrender.com"
PORT = int(os.environ.get("PORT", 8080))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
ai_client = Groq(api_key=GROQ_API_KEY)

class IELTSMockState(StatesGroup):
    part1_q1 = State()
    part2_cue = State()
    part3_q1 = State()

EXAMINER_PROMPT = (
    "You are a strict IELTS examiner. Ask ONE question at a time. "
    "Do not repeat questions. Be professional and neutral."
)

# --- YORDAMCHI FUNKSIYALAR (TEPADA) ---
async def transcribe_voice(message: types.Message) -> str:
    voice_id = message.voice.file_id
    file = await bot.get_file(voice_id)
    path = f"{voice_id}.ogg"
    await bot.download_file(file.file_path, path)
    with open(path, "rb") as f:
        tr = ai_client.audio.transcriptions.create(file=(path, f.read()), model="whisper-large-v3")
    os.remove(path)
    return tr.text

async def send_examiner_voice(message: types.Message, text: str):
    path = f"ex_{message.chat.id}.mp3"
    comm = edge_tts.Communicate(text, "en-US-JennyNeural")
    await comm.save(path)
    await message.answer_voice(types.FSInputFile(path))
    if os.path.exists(path): os.remove(path)

# --- HANDLERLAR ---
@dp.message(CommandStart())
async def start(message: types.Message):
    await message.answer("Salom! ShavkatoV AI botiga xush kelibsiz. /mock_ielts ni bosing.")

@dp.message(Command("mock_ielts"))
async def start_ielts_mock(message: types.Message, state: FSMContext):
    await state.clear()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Testni boshlash", callback_data="start_exam")]
    ])
    await message.answer("🎓 <b>IELTS Mock Test:</b>\n3 qismdan iborat. Ovozli xabar bilan javob bering.", 
                         reply_markup=kb, parse_mode="HTML")

@dp.callback_query(F.data == "start_exam")
async def start_exam(callback: types.CallbackQuery, state: FSMContext):
    completion = ai_client.chat.completions.create(
        messages=[{"role": "system", "content": EXAMINER_PROMPT}, {"role": "user", "content": "Ask first Part 1 question."}],
        model="llama-3.3-70b-versatile",
    )
    q = completion.choices[0].message.content
    await callback.message.answer(f"🗣 <b>Part 1:</b>\n{q}", parse_mode="HTML")
    await send_examiner_voice(callback.message, q)
    await state.update_data(history=[{"role": "examiner", "content": q}])
    await state.set_state(IELTSMockState.part1_q1)

@dp.message(IELTSMockState.part1_q1, F.voice)
async def handle_p1(message: types.Message, state: FSMContext):
    text = await transcribe_voice(message)
    data = await state.get_data()
    history = data.get("history")
    history.append({"role": "candidate", "content": text})
    
    # Yakuniy natija chiqarish (test uchun qisqartirilgan)
    await message.answer("🏁 <b>Test tugadi!</b>\n\n🏆 <b>Overall: 7.5</b>\n✅ <b>Fluency: 7.0</b>\n✅ <b>Pronunciation: 8.0</b>")
    await state.clear()

@dp.message(F.voice)
async def handle_normal_voice(message: types.Message):
    text = await transcribe_voice(message)
    comp = ai_client.chat.completions.create(
        messages=[{"role": "user", "content": text}],
        model="llama-3.3-70b-versatile"
    )
    await message.answer(comp.choices[0].message.content)

# --- SERVER ---
async def handle_webhook(request):
    data = await request.json()
    await dp.feed_update(bot, types.Update(**data))
    return web.Response(text="OK")

async def on_startup(app):
    await bot.set_webhook(f"{WEBHOOK_URL}/webhook")

if __name__ == "__main__":
    app = web.Application()
    app.router.add_post("/webhook", handle_webhook)
    app.on_startup.append(on_startup)
    web.run_app(app, host="0.0.0.0", port=PORT)
