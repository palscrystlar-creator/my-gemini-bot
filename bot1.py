import os
import asyncio
import random
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web
from groq import Groq
import edge_tts

# --- CONFIG ---
BOT_TOKEN = "8799568905:AAGY-PYkbve9LkNp2Fy922FAibTopmomu5s"
GROQ_API_KEY = "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"
PORT = int(os.environ.get("PORT", 8080))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
ai_client = Groq(api_key=GROQ_API_KEY)

class IELTSMockState(StatesGroup):
    part1_q1 = State(); part1_q2 = State(); part1_q3 = State()
    part2_cue = State()
    part3_q1 = State(); part3_q2 = State(); part3_q3 = State()

# --- EXAMINER LOGIC (Natural Flow) ---
async def get_natural_question(history, context):
    prompt = f"""
    You are a professional IELTS Examiner (British accent style).
    Context: {context}
    History of conversation: {history}
    Goal: Ask only one question. 
    Rule: Before asking, acknowledge the candidate's previous answer with a short natural phrase like "That's interesting" or "I see". 
    Do not use meta-language like "Next question". Be strict but polite.
    """
    response = ai_client.chat.completions.create(
        messages=[{"role": "system", "content": prompt}],
        model="llama-3.3-70b-versatile"
    )
    return response.choices[0].message.content

async def send_examiner_voice(message, text, voice="en-GB-ArthurNeural"): # Britaniya aksenti
    path = f"ex_{message.chat.id}.mp3"
    comm = edge_tts.Communicate(text, voice)
    await comm.save(path)
    await message.answer_voice(types.FSInputFile(path))
    if os.path.exists(path): os.remove(path)

async def transcribe(message):
    file = await bot.get_file(message.voice.file_id)
    path = f"{message.voice.file_id}.ogg"
    await bot.download_file(file.file_path, path)
    with open(path, "rb") as f:
        tr = ai_client.audio.transcriptions.create(file=(path, f.read()), model="whisper-large-v3")
    os.remove(path)
    return tr.text

# --- MOCK HANDLERS ---
@dp.message(Command("mock_ielts"))
async def start_mock(message: types.Message, state: FSMContext):
    await state.clear()
    intro = "Good morning. I am your examiner today. Let's start with Part 1. Could you tell me your full name, please?"
    await message.answer(f"🗣 <b>Examiner:</b> {intro}", parse_mode="HTML")
    await send_examiner_voice(message, intro)
    await state.set_state(IELTSMockState.part1_q1)
    await state.update_data(history=[])

@dp.message(IELTSMockState.part1_q1, F.voice)
async def p1_q1(msg: types.Message, state: FSMContext):
    text = await transcribe(msg)
    data = await state.get_data()
    hist = data['history'] + [{"role": "candidate", "content": text}]
    
    q2 = await get_natural_question(hist, "Part 1 follow-up")
    await msg.answer(f"🗣 <b>Examiner:</b> {q2}", parse_mode="HTML")
    await send_examiner_voice(msg, q2)
    await state.update_data(history=hist + [{"role": "examiner", "content": q2}])
    await state.set_state(IELTSMockState.part1_q2)

# ... bu mantiqni part3_q3 gacha davom ettiring ...
# (Qolgan barcha handlerlar xuddi shu prinsipda: transcribe -> history -> natural_q -> send_voice)

@dp.message(CommandStart())
async def start(msg: types.Message):
    await msg.answer("IELTS Mock yoki Practice rejimini tanlang.")

# --- MAIN ---
async def main():
    bot_commands = [
        types.BotCommand(command="mock_ielts", description="Imtihonni boshlash"),
        types.BotCommand(command="practice", description="Erkin suhbat")
    ]
    await bot.set_my_commands(bot_commands)
    
    app = web.Application()
    # Webhook va server qismi...
    # (Oldingi koddagi kabi qoldiring)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
