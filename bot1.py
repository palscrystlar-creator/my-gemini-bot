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

# Server va Bot sozlamalari
BOT_TOKEN = "8799568905:AAGY-PYkbve9LkNp2Fy922FAibTopmomu5s"
GROQ_API_KEY = "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"
WEBHOOK_URL = "https://my-gemini-bot-1-14qh.onrender.com"
PORT = int(os.environ.get("PORT", 8080))

storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage)
ai_client = Groq(api_key=GROQ_API_KEY)

class IELTSMockState(StatesGroup):
    part1_q1 = State()
    part1_q2 = State()
    part1_q3 = State()
    part2_cue = State()
    part3_q1 = State()
    part3_q2 = State()
    part3_q3 = State()

SYSTEM_PROMPT = (
    "Sizning ismingiz 'ShavkatoV AI'. Foydalanuvchi qaysi tilda gapirsa, faqat o'sha tilda javob bering. "
    "Agar o'zbekcha gapirsa, faqat toza o'zbekcha javob qaytaring."
)

EXAMINER_PROMPT = (
    "You are an expert IELTS Speaking Examiner. Your tone is professional, polite, and strict. "
    "Strictly follow these rules: "
    "1. Ask ONLY ONE question at a time. "
    "2. After receiving the candidate's answer, acknowledge it and immediately move to the next relevant question. "
    "3. Never ask multiple questions in a single turn. "
    "4. Do not provide conversational filler or feedback; just act as the examiner."
)

# Eski qator:
# async def send_examiner_voice(message: types.Message, text: str, voice="en-US-BrianNeural"):

# YANGI QATOR:
async def send_examiner_voice(message: types.Message, text: str, voice="en-US-JennyNeural"):
    reply_voice_path = f"examiner_{message.chat.id}.mp3"
    try:
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(reply_voice_path)
        voice_file = types.FSInputFile(reply_voice_path)
        await message.answer_voice(voice_file)
    except Exception as e:
        await message.answer(f"[Voice Error] {text}")
    finally:
        if os.path.exists(reply_voice_path):
            try: os.remove(reply_voice_path)
            except: pass

@dp.message(CommandStart())
async def start_command(message: types.Message):
    welcome_text = (
        f"<b>Salom, {message.from_user.full_name}!</b> 👋\n\n"
        f"🤖 Men <b>ShavkatoV AI</b> botiman.\n"
        f"🎙 Men bilan matnli yoki ovozli suhbat qurishingiz mumkin.\n\n"
        f"🏆 <b>IELTS Speaking Mock imtihoni uchun:</b> /mock_ielts buyrug'ini yuboring!"
    )
    await message.answer(welcome_text, parse_mode="HTML")

@dp.message(Command("mock_ielts"))
async def start_ielts_mock(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("🎬 <b>Welcome to the Full IELTS Speaking Mock Test!</b>\n"
                         "This test consists of Part 1, Part 2, and Part 3.\n"
                         "Please reply to every question using <b>VOICE MESSAGES</b>.🎙\n\n"
                         "<i>Starting Part 1...</i>", parse_mode="HTML")
    try:
        completion = ai_client.chat.completions.create(
            messages=[
                {"role": "system", "content": EXAMINER_PROMPT},
                {"role": "user", "content": "Generate a common IELTS Speaking Part 1 topic question. Ask just one question."}
            ],
            model="llama-3.3-70b-versatile",
        )
        q1 = completion.choices[0].message.content
        await message.answer(f"🗣 <b>Part 1 - Question 1:</b>\n{q1}", parse_mode="HTML")
        await send_examiner_voice(message, q1)
        await state.set_state(IELTSMockState.part1_q1)
        await state.update_data(p1_q1=q1, history=[])
    except Exception as e:
        await message.answer(f"Xatolik: {str(e)}")

async def transcribe_voice(message: types.Message) -> str:
    voice_id = message.voice.file_id
    file = await bot.get_file(voice_id)
    local_voice_path = f"{voice_id}.ogg"
    await bot.download_file(file.file_path, local_voice_path)
    try:
        with open(local_voice_path, "rb") as audio_file:
            transcription = ai_client.audio.transcriptions.create(
                file=(local_voice_path, audio_file.read()),
                model="whisper-large-v3",
            )
        return transcription.text
    except:
        return ""
    finally:
        if os.path.exists(local_voice_path): os.remove(local_voice_path)

@dp.message(IELTSMockState.part1_q1, F.voice)
async def p1_q1_handler(message: types.Message, state: FSMContext):
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    text = await transcribe_voice(message)
    if not text: return
    data = await state.get_data()
    history = data.get("history", [])
    history.append({"role": "examiner", "content": data.get("p1_q1")})
    history.append({"role": "candidate", "content": text})
    completion = ai_client.chat.completions.create(
        messages=[{"role": "system", "content": EXAMINER_PROMPT}, {"role": "user", "content": f"Ask the next Part 1 question. History: {history}"}],
        model="llama-3.3-70b-versatile",
    )
    q2 = completion.choices[0].message.content
    await message.answer(f"🗣 <b>Part 1 - Question 2:</b>\n{q2}", parse_mode="HTML")
    await send_examiner_voice(message, q2)
    await state.update_data(p1_q2=q2, history=history)
    await state.set_state(IELTSMockState.part1_q2)

@dp.message(IELTSMockState.part1_q2, F.voice)
async def p1_q2_handler(message: types.Message, state: FSMContext):
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    text = await transcribe_voice(message)
    if not text: return
    data = await state.get_data()
    history = data.get("history")
    history.append({"role": "examiner", "content": data.get("p1_q2")})
    history.append({"role": "candidate", "content": text})
    completion = ai_client.chat.completions.create(
        messages=[{"role": "system", "content": EXAMINER_PROMPT}, {"role": "user", "content": f"Ask the next Part 1 question. History: {history}"}],
        model="llama-3.3-70b-versatile",
    )
    q3 = completion.choices[0].message.content
    await message.answer(f"🗣 <b>Part 1 - Question 3:</b>\n{q3}", parse_mode="HTML")
    await send_examiner_voice(message, q3)
    await state.update_data(p1_q3=q3, history=history)
    await state.set_state(IELTSMockState.part1_q3)

@dp.message(IELTSMockState.part1_q3, F.voice)
async def p1_q3_handler(message: types.Message, state: FSMContext):
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    text = await transcribe_voice(message)
    if not text: return
    data = await state.get_data()
    history = data.get("history")
    history.append({"role": "examiner", "content": data.get("p1_q3")})
    history.append({"role": "candidate", "content": text})
    await message.answer(" Moving to <b>Part 2 (Cue Card)</b>.", parse_mode="HTML")
    completion = ai_client.chat.completions.create(
        messages=[{"role": "system", "content": "Provide a complete IELTS Speaking Part 2 Cue Card."}],
        model="llama-3.3-70b-versatile",
    )
    cue_card = completion.choices[0].message.content
    await message.answer(f"📋 <b>PART 2 - CUE CARD:</b>\n\n{cue_card}", parse_mode="HTML")
    await send_examiner_voice(message, "Look at the cue card. Start speaking when ready.")
    await state.update_data(p2_cue=cue_card, history=history)
    await state.set_state(IELTSMockState.part2_cue)

@dp.message(IELTSMockState.part2_cue, F.voice)
async def p2_handler(message: types.Message, state: FSMContext):
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    text = await transcribe_voice(message)
    if not text: return
    data = await state.get_data()
    history = data.get("history")
    history.append({"role": "examiner", "content": "Part 2"})
    history.append({"role": "candidate", "content": text})
    await message.answer(" Proceeding to <b>Part 3</b>.", parse_mode="HTML")
    completion = ai_client.chat.completions.create(
        messages=[{"role": "system", "content": EXAMINER_PROMPT}, {"role": "user", "content": f"Ask the first Part 3 question based on: {data.get('p2_cue')}"}],
        model="llama-3.3-70b-versatile",
    )
    p3_q1 = completion.choices[0].message.content
    await message.answer(f"🗣 <b>Part 3 - Question 1:</b>\n{p3_q1}", parse_mode="HTML")
    await send_examiner_voice(message, p3_q1)
    await state.update_data(p3_q1=p3_q1, history=history)
    await state.set_state(IELTSMockState.part3_q1)

@dp.message(IELTSMockState.part3_q1, F.voice)
async def p3_q1_handler(message: types.Message, state: FSMContext):
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    text = await transcribe_voice(message)
    if not text: return
    data = await state.get_data()
    history = data.get("history")
    history.append({"role": "examiner", "content": data.get("p3_q1")})
    history.append({"role": "candidate", "content": text})
    completion = ai_client.chat.completions.create(
        messages=[{"role": "system", "content": EXAMINER_PROMPT}, {"role": "user", "content": f"Ask next Part 3 question. History: {history}"}],
        model="llama-3.3-70b-versatile",
    )
    p3_q2 = completion.choices[0].message.content
    await message.answer(f"🗣 <b>Part 3 - Question 2:</b>\n{p3_q2}", parse_mode="HTML")
    await send_examiner_voice(message, p3_q2)
    await state.update_data(p3_q2=p3_q2, history=history)
    await state.set_state(IELTSMockState.part3_q2)

@dp.message(IELTSMockState.part3_q2, F.voice)
async def p3_q2_handler(message: types.Message, state: FSMContext):
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    text = await transcribe_voice(message)
    if not text: return
    data = await state.get_data()
    history = data.get("history")
    history.append({"role": "examiner", "content": data.get("p3_q2")})
    history.append({"role": "candidate", "content": text})
    completion = ai_client.chat.completions.create(
        messages=[{"role": "system", "content": EXAMINER_PROMPT}, {"role": "user", "content": f"Ask final Part 3 question. History: {history}"}],
        model="llama-3.3-70b-versatile",
    )
    p3_q3 = completion.choices[0].message.content
    await message.answer(f"🗣 <b>Part 3 - Question 3:</b>\n{p3_q3}", parse_mode="HTML")
    await send_examiner_voice(message, p3_q3)
    await state.update_data(p3_q3=p3_q3, history=history)
    await state.set_state(IELTSMockState.part3_q3)

@dp.message(IELTSMockState.part3_q3, F.voice)
async def p3_q3_handler(message: types.Message, state: FSMContext):
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    await message.answer("🏁 <i>Test tugadi! Tahlil qilinmoqda...</i>")
    text = await transcribe_voice(message)
    if not text: return
    data = await state.get_data()
    history = data.get("history")
    history.append({"role": "examiner", "content": data.get("p3_q3")})
    history.append({"role": "candidate", "content": text})
    try:
        report_prompt = f"Analyze this IELTS interview: {history}. Provide a detailed report in Uzbek with sections: Score, Fluency, Lexical, Grammar, Tips. Use '---' as a divider."
        completion = ai_client.chat.completions.create(
            messages=[{"role": "user", "content": report_prompt}],
            model="llama-3.3-70b-versatile",
        )
        sections = completion.choices[0].message.content.split("---")
        for section in sections:
            if section.strip():
                await message.answer(section.strip())
    finally:
        await state.clear()

@dp.message(F.text)
async def chat_with_ai(message: types.Message):
    chat_completion = ai_client.chat.completions.create(
        messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": message.text}],
        model="llama-3.3-70b-versatile",
    )
    await message.answer(chat_completion.choices[0].message.content)

async def handle_webhook(request):
    url = str(request.url)
    if "/webhook" in url:
        request_data = await request.json()
        update = types.Update(**request_data)
        await dp.feed_update(bot, update)
    return web.Response(text="OK")

async def on_startup(app):
    await bot.set_webhook(f"{WEBHOOK_URL}/webhook")

if __name__ == "__main__":
    app = web.Application()
    app.router.add_post("/webhook", handle_webhook)
    app.on_startup.append(on_startup)
    web.run_app(app, host="0.0.0.0", port=PORT)
