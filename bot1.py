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
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
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
    "You are a strictly professional, neutral, and polite IELTS Speaking Examiner. "
    "Your goal is to conduct a realistic IELTS Speaking test. "
    "FOLLOW THESE RULES STRICTLY:\n"
    "1. ASK ONLY ONE QUESTION AT A TIME. Never ask two questions at once.\n"
    "2. VARIETY: You must generate a unique and different question every single time. "
    "   Do not repeat questions. If the previous question was about 'hometown', ask about 'hobbies' or 'study'.\n"
    "3. TONE: Be formal, encouraging, but do not provide feedback or conversational filler "
    "   like 'That is good'. Simply listen and move to the next question.\n"
    "4. NO REPETITION: If the user provides an answer, acknowledge it and transition to "
    "   the next relevant sub-topic immediately.\n"
    "5. FORMAT: Provide only the question text. No conversational chatter."
)

async def send_examiner_voice(message: types.Message, text: str, voice="en-US-BrianNeural"):
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

# ==================== IELTS SPEAKING MOCK EXAM ====================

@dp.message(Command("mock_ielts"))
async def start_ielts_mock(message: types.Message, state: FSMContext):
    await state.clear() # Oldingi ma'lumotlarni tozalaymiz
    
    explanation = (
        "🎓 <b>IELTS Speaking Mock Test ga xush kelibsiz!</b>\n\n"
        "Bu imtihon 3 qismdan iborat:\n"
        "🔹 <b>Part 1:</b> 3 ta umumiy mavzudagi savol.\n"
        "🔹 <b>Part 2:</b> 1 ta Cue Card (mavzu) bo‘yicha 2 daqiqa gapirish.\n"
        "🔹 <b>Part 3:</b> Mavzu yuzasidan chuqurroq savollar.\n\n"
        "⚠️ <b>Muhim qoida:</b> Har bir savolga faqat <b>OVZOLI XABAR</b> bilan javob bering. "
        "Test oxirida sizga ballar va tahliliy hisobot yuboraman.\n\n"
        "Tayyor bo‘lsangiz, tugmani bosing:"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Testni boshlash", callback_data="start_exam")]
    ])
    
    await message.answer(explanation, reply_markup=keyboard, parse_mode="HTML")

# 2. Tugma bosilganda imtihonni boshlovchi funksiya
@dp.callback_query(F.data == "start_exam")
async def process_start_exam(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.delete() # Informatsion xabarni o'chirib tashlaymiz
    await callback.message.answer("🎬 <b>Imtihon boshlandi! Diqqat bilan eshiting...</b>", parse_mode="HTML")
    
    # Birinchi savolni generatsiya qilish
    try:
        completion = ai_client.chat.completions.create(
            messages=[
                {"role": "system", "content": EXAMINER_PROMPT},
                {"role": "user", "content": "Generate a unique IELTS Speaking Part 1 question. Do not repeat."}
            ],
            model="llama-3.3-70b-versatile",
            temperature=1.0 # Har safar yangi savol uchun
        )
        q1 = completion.choices[0].message.content
        
        await callback.message.answer(f"🗣 <b>Part 1 - Question 1:</b>\n{q1}", parse_mode="HTML")
        await send_examiner_voice(callback.message, q1)
        
        await state.update_data(p1_q1=q1, history=[])
        await state.set_state(IELTSMockState.part1_q1)
        
    except Exception as e:
        await callback.message.answer(f"Xatolik: {str(e)}")

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
        messages=[{"role": "system", "content": EXAMINER_PROMPT}, {"role": "user", "content": f"Ask the third question for Part 1 based on: {history}"}],
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
        messages=[{"role": "system", "content": "You are an IELTS examiner. Provide a complete IELTS Speaking Part 2 Cue Card task block."}],
        model="llama-3.3-70b-versatile",
    )
    cue_card = completion.choices[0].message.content
    await message.answer(f"📋 <b>PART 2 - CUE CARD:</b>\n\n{cue_card}\n\n<i>🔴 Please record your voice now (1-2 minutes).</i>", parse_mode="HTML")
    await send_examiner_voice(message, "Please look at the cue card on your screen. Start your voice message whenever you are ready.")
    await state.update_data(p2_cue=cue_card, history=history)
    await state.set_state(IELTSMockState.part2_cue)

@dp.message(IELTSMockState.part2_cue, F.voice)
async def p2_handler(message: types.Message, state: FSMContext):
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    text = await transcribe_voice(message)
    if not text: return
    data = await state.get_data()
    history = data.get("history")
    history.append({"role": "examiner", "content": f"Part 2 Cue Card: {data.get('p2_cue')}"})
    history.append({"role": "candidate", "content": text})
    
    await message.answer(" Proceeding to <b>Part 3 (Discussion)</b>.", parse_mode="HTML")
    completion = ai_client.chat.completions.create(
        messages=[{"role": "system", "content": EXAMINER_PROMPT}, {"role": "user", "content": f"Ask the first deep question for Part 3 based on Part 2 topic."}],
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
        messages=[{"role": "system", "content": EXAMINER_PROMPT}, {"role": "user", "content": f"Ask the second Part 3 question based on: {history}"}],
        model="llama-3.3-70b-versatile",
    )
    p3_q2 = completion.choices[0].message.content
    await message.answer(f"🗣 <b>Part 3 - Question 2:</b>\n{p3_q2}", parse_mode="HTML")
    await send_examiner_voice(message, p3_q2)
    await state.update_data(p3_q2=p3_q2, history=history)
    await state.set_state(IELTSMockState.part3_q2)

@dp.message(IELTSMockState.part3_q3, F.voice)
async def p3_q3_handler(message: types.Message, state: FSMContext):
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    await message.answer("🏁 <i>Test tugadi! Natijalar hisoblanmoqda...</i>", parse_mode="HTML")
    
    text = await transcribe_voice(message)
    data = await state.get_data()
    history = data.get("history", [])
    history.append({"role": "candidate", "content": text})
    
    # AI dan aniq ballarni talab qilamiz
    report_prompt = (
        "Analyze this IELTS Speaking interview. Provide the result in this format:\n\n"
        "🏆 <b>Overall Band Score: [0.0-9.0]</b>\n"
        "---------------------------\n"
        "✅ <b>Fluency and Coherence:</b> [Score] - [Reason]\n"
        "✅ <b>Lexical Resource:</b> [Score] - [Reason]\n"
        "✅ <b>Grammatical Range:</b> [Score] - [Reason]\n"
        "✅ <b>Pronunciation:</b> [Score] - [Reason]\n\n"
        "💡 <b>Tips for improvement:</b> [Short advice]\n\n"
        f"Interview Data: {history}"
    )
    
    try:
        completion = ai_client.chat.completions.create(
            messages=[{"role": "user", "content": report_prompt}],
            model="llama-3.3-70b-versatile",
        )
        report = completion.choices[0].message.content
        await message.answer(report, parse_mode="HTML")
    except Exception as e:
        await message.answer("Natijalarni shakllantirishda xatolik yuz berdi.")
    finally:
        await state.clear()

# --- STANDART SUHBAT REJIMLARI ---
@dp.message(F.text)
async def chat_with_ai(message: types.Message):
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    try:
        chat_completion = ai_client.chat.completions.create(
            messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": message.text}],
            model="llama-3.3-70b-versatile",
        )
        await message.answer(chat_completion.choices[0].message.content)
    except Exception as e:
        await message.answer(f"Xatolik: {str(e)}")

@dp.message(F.voice)
async def handle_normal_voice(message: types.Message):
    await bot.send_chat_action(chat_id=message.chat.id, action="record_voice")
    user_text = await transcribe_voice(message)
    if not user_text: return
    try:
        chat_completion = ai_client.chat.completions.create(
            messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user_text}],
            model="llama-3.3-70b-versatile",
        )
        ai_response = chat_completion.choices[0].message.content
        voice_model = "uz-UZ-MadinaNeural"
        if any(word in user_text.lower() for word in ['hello', 'what', 'is', 'your', 'name']):
            voice_model = "en-US-EmmaNeural"
        reply_voice_path = f"reply_{message.voice.file_id}.mp3"
        communicate = edge_tts.Communicate(ai_response, voice_model)
        await communicate.save(reply_voice_path)
        await message.answer_voice(types.FSInputFile(reply_voice_path), caption=f"✍️ <i>Siz aytdingiz: {user_text}</i>", parse_mode="HTML")
        if os.path.exists(reply_voice_path): os.remove(reply_voice_path)
    except Exception as e:
        await message.answer(f"Xatolik: {str(e)}")

async def handle_webhook(request):
    url = str(request.url)
    index = url.rfind("/webhook")
    if index != -1:
        request_data = await request.json()
        update = types.Update(**request_data)
        await dp.feed_update(bot, update)
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
