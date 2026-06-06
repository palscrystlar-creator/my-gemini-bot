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
import uuid
import sqlite3
# Server va Bot sozlamalari
BOT_TOKEN = "8799568905:AAGY-PYkbve9LkNp2Fy922FAibTopmomu5s"
GROQ_API_KEY = "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"
WEBHOOK_URL = "https://my-gemini-bot-1-14qh.onrender.com"
PORT = int(os.environ.get("PORT", 8080))

storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
user_histories = {}
dp = Dispatcher(storage=storage)
ai_client = Groq(api_key=GROQ_API_KEY)

# IELTS Speaking Mock holatlari
class IELTSMockState(StatesGroup):
    part1_q1 = State()
    part1_q2 = State()
    part1_q3 = State()
    part2_cue = State()
    part3_q1 = State()
    part3_q2 = State()
    part3_q3 = State()

# Tizim qoidalari
SYSTEM_PROMPT = (
    "Sizning ismingiz 'ShavkatoV AI'. Foydalanuvchi qaysi tilda gapirsa, faqat o'sha tilda javob bering. "
    "Agar o'zbekcha gapirsa, faqat toza o'zbekcha javob qaytaring."
)

EXAMINER_PROMPT = (
    "You are an expert IELTS Speaking Examiner.Dont repeat a queston. Your tone should be professional, angry, and strict. "
    "Ask only ONE clear question at a time according to the part requirements. Do not output anything else."
)
def init_db():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                      (user_id INTEGER PRIMARY KEY, name TEXT, last_score REAL)''')
    conn.commit()
    conn.close()

def save_user_score(user_id, name, score):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO users VALUES (?, ?, ?)", (user_id, name, score))
    conn.commit()
    conn.close()
    init_db()
# Matnni ovozga o'giriuvchi yordamchi funksiya
async def send_examiner_voice(message: types.Message, text: str, voice="en-US-BrianNeural"):
    reply_voice_path = f"examiner_{message.chat.id}_{uuid.uuid4().hex}.mp3"
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
        f"🎙 Oddiy rejimda men bilan matnli yoki ovozli suhbat qurishingiz mumkin.\n\n"
        f"🏆 <b>To'liq IELTS Speaking Mock imtihonini topshirish uchun:</b> /mock_ielts buyrug'ini yuboring!"
    )
    await message.answer(welcome_text, parse_mode="HTML")

# ==================== IELTS SPEAKING MOCK EXAM ====================

@dp.message(Command("mock_ielts"))
async def start_ielts_mock(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("🎬 <b>Welcome to the Full IELTS Speaking Mock Test!</b>\n"
                         "This test consists of Part 1, Part 2, and Part 3.\n"
                         "Please reply to every question using <b>VOICE MESSAGES</b> (Ovozli xabar).🎙\n\n"
                         "<i>Starting Part 1 (Introduction and Interview)...</i>", parse_mode="HTML")
    
    # Part 1 uchun 1-savolni generatsiya qilamiz
    try:
        completion = ai_client.chat.completions.create(
            messages=[
                {"role": "system", "content": EXAMINER_PROMPT},
                {"role": "user", "content": "Generate a common IELTS Speaking Part 1 topic question (e.g., about home, work, studies, or hobbies). Ask just one question."}
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

# Uni quyidagiga almashtiring:
async def transcribe_voice(message: types.Message) -> str:
    voice_id = message.voice.file_id
    file = await bot.get_file(voice_id)
    local_voice_path = f"{voice_id}.ogg"
    await bot.download_file(file.file_path, local_voice_path)
    
    try:
        with open(local_voice_path, "rb") as audio_file:
            transcription = ai_client.audio.transcriptions.create(
                file=(local_voice_path, audio_file.read()), # Fayl nomi va binar ma'lumot
                model="whisper-large-v3",
            )
        return transcription.text
    except Exception as e:
        print(f"Transkripsiya xatosi: {e}") # Konsolda ko'rinadi
        return ""
    finally:
        if os.path.exists(local_voice_path): os.remove(local_voice_path)

# --- PART 1: Q1 ANSWER -> ASK Q2 ---
@dp.message(IELTSMockState.part1_q1, F.voice)
async def p1_q1_handler(message: types.Message, state: FSMContext):
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    text = await transcribe_voice(message)
    if not text:
        await message.answer("I couldn't hear you clearly. Please repeat your answer via voice.")
        return
    
    data = await state.get_data()
    history = data.get("history", [])
    history.append({"role": "examiner", "content": data.get("p1_q1")})
    history.append({"role": "candidate", "content": text})
    
    # Navbatdagi savol
    completion = ai_client.chat.completions.create(
        messages=[{"role": "system", "content": EXAMINER_PROMPT}, {"role": "user", "content": f"Based on this interview context: {history}, ask the second follow-up question for Part 1."}],
        model="llama-3.3-70b-versatile",
    )
    q2 = completion.choices[0].message.content
    await message.answer(f"🗣 <b>Part 1 - Question 2:</b>\n{q2}", parse_mode="HTML")
    await send_examiner_voice(message, q2)
    
    await state.update_data(p1_q2=q2, history=history)
    await state.set_state(IELTSMockState.part1_q2)

# --- PART 1: Q2 ANSWER -> ASK Q3 ---
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
        messages=[{"role": "system", "content": EXAMINER_PROMPT}, {"role": "user", "content": f"Ask the third and final question for Part 1 based on: {history}"}],
        model="llama-3.3-70b-versatile",
    )
    q3 = completion.choices[0].message.content
    await message.answer(f"🗣 <b>Part 1 - Question 3:</b>\n{q3}", parse_mode="HTML")
    await send_examiner_voice(message, q3)
    
    await state.update_data(p1_q3=q3, history=history)
    await state.set_state(IELTSMockState.part1_q3)

# --- PART 1: Q3 ANSWER -> START PART 2 (CUE CARD) ---
@dp.message(IELTSMockState.part1_q3, F.voice)
async def p1_q3_handler(message: types.Message, state: FSMContext):
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    text = await transcribe_voice(message)
    if not text: return
    
    data = await state.get_data()
    history = data.get("history")
    history.append({"role": "examiner", "content": data.get("p1_q3")})
    history.append({"role": "candidate", "content": text})
    
    await message.answer(" Moving to <b>Part 2 (Cue Card / Long Turn)</b>.\n"
                         "I will give you a topic. You should think about it and speak for 1 to 2 minutes.", parse_mode="HTML")
    
    completion = ai_client.chat.completions.create(
        messages=[{"role": "system", "content": "You are an IELTS examiner. Provide a complete IELTS Speaking Part 2 Cue Card task block. It must have a main topic sentence and 3-4 bullet points (e.g., Describe a book you read...)."}],
        model="llama-3.3-70b-versatile",
    )
    cue_card = completion.choices[0].message.content
    await message.answer(f"📋 <b>PART 2 - CUE CARD:</b>\n\n{cue_card}\n\n<i>🔴 Please record your long turn answer now (Speak for 1-2 minutes in one voice message).</i>", parse_mode="HTML")
    await send_examiner_voice(message, "Please look at the cue card on your screen. You have one to two minutes to talk about this topic. Whenever you are ready, start your voice message.")
    
    await state.update_data(p2_cue=cue_card, history=history)
    await state.set_state(IELTSMockState.part2_cue)

# --- PART 2 ANSWER -> START PART 3 (Q1) ---
@dp.message(IELTSMockState.part2_cue, F.voice)
async def p2_handler(message: types.Message, state: FSMContext):
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    text = await transcribe_voice(message)
    if not text: return
    
    data = await state.get_data()
    history = data.get("history")
    history.append({"role": "examiner", "content": f"Part 2 Cue Card Task: {data.get('p2_cue')}"})
    history.append({"role": "candidate", "content": f"Part 2 Long Turn Response: {text}"})
    
    await message.answer(" Thank you. Let's proceed to <b>Part 3 (Two-way Discussion)</b>.\n"
                         "I will ask you some abstract and deeper questions related to the Part 2 topic.", parse_mode="HTML")
    
    completion = ai_client.chat.completions.create(
        messages=[{"role": "system", "content": EXAMINER_PROMPT}, {"role": "user", "content": f"Based on the Part 2 topic, ask the first deep analytical question for Part 3."}],
        model="llama-3.3-70b-versatile",
    )
    p3_q1 = completion.choices[0].message.content
    await message.answer(f"🗣 <b>Part 3 - Question 1:</b>\n{p3_q1}", parse_mode="HTML")
    await send_examiner_voice(message, p3_q1)
    
    await state.update_data(p3_q1=p3_q1, history=history)
    await state.set_state(IELTSMockState.part3_q1)

# --- PART 3: Q1 ANSWER -> ASK Q2 ---
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
        messages=[{"role": "system", "content": EXAMINER_PROMPT}, {"role": "user", "content": f"Ask the second deep Part 3 question based on: {history}"}],
        model="llama-3.3-70b-versatile",
    )
    p3_q2 = completion.choices[0].message.content
    await message.answer(f"🗣 <b>Part 3 - Question 2:</b>\n{p3_q2}", parse_mode="HTML")
    await send_examiner_voice(message, p3_q2)
    
    await state.update_data(p3_q2=p3_q2, history=history)
    await state.set_state(IELTSMockState.part3_q2)

# --- PART 3: Q2 ANSWER -> ASK Q3 ---
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
        messages=[{"role": "system", "content": EXAMINER_PROMPT}, {"role": "user", "content": f"Ask the third and final analytical question for Part 3 based on: {history}"}],
        model="llama-3.3-70b-versatile",
    )
    p3_q3 = completion.choices[0].message.content
    await message.answer(f"🗣 <b>Part 3 - Question 3 (Final):</b>\n{p3_q3}", parse_mode="HTML")
    await send_examiner_voice(message, p3_q3)
    
    await state.update_data(p3_q3=p3_q3, history=history)
    await state.set_state(IELTSMockState.part3_q3)

# --- PART 3: Q3 ANSWER -> GENERATE FINAL FEEDBACK AND BAND SCORE ---
@dp.message(IELTSMockState.part3_q3, F.voice)
async def p3_q3_handler(message: types.Message, state: FSMContext):
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    await message.answer("🏁 <i>Test tugadi! Tahlil qilinmoqda, iltimos kuting...</i>")
    
    text = await transcribe_voice(message)
    if not text: return
    
    data = await state.get_data()
    history = data.get("history")
    history.append({"role": "examiner", "content": data.get("p3_q3")})
    history.append({"role": "candidate", "content": text})
    
    try:
        # AI dan hisobotni maxsus qismlarga bo'lingan formatda so'raymiz
        report_prompt = (
            f"Analyze this IELTS interview: {history}\n\n"
            f"Generate a detailed report in Uzbek. You MUST strictly separate the sections using '---' divider. "
            f"Format exactly like this:\n"
            f"🏆 **OFFICIAL IELTS SPEAKING REPORT** 🏆\n"
            f"**Umumiy Baholash Balli:** [Score]\n"
            f"---"
            f"📈 **1. Fluency and Coherence:** [Text]\n"
            f"---"
            f"🔤 **2. Lexical Resource:** [Text]\n"
            f"---"
            f"⚖️ **3. Grammatical Range:** [Text]\n"
            f"---"
            f"🛠️ **4. Key Corrections:** [Text]\n"
            f"---"
            f"💡 **5. Tips to Improve:** [Text]"
        )
        
        completion = ai_client.chat.completions.create(
            messages=[{"role": "user", "content": report_prompt}],
            model="llama-3.3-70b-versatile",
        )
        report_content = completion.choices[0].message.content
        
        # Hisobotni bo'limlarga ajratib, har biriga alohida ovoz beramiz
        sections = report_content.split("---")
        
        await message.answer("📊 <b>SIZNING TO'LIQ IELTS MOCK HISOBOTINGIZ:</b>\n\n(Har bir bo'lim matni ostida uning o'zbekcha ovozli audiosi ham taqdim etiladi 👇)")
        
        for index, section in enumerate(sections):
            clean_section = section.strip()
            if clean_section:
                # Foydalanuvchiga matnni yuboramiz
                await message.answer(clean_section)
                
                # Ovozli fayl yaratamiz (O'zbekcha Madina ovozi)
                voice_path = f"report_part_{index}_{message.chat.id}.mp3"
                communicate = edge_tts.Communicate(clean_section.replace("**", "").replace("*", ""), "uz-UZ-MadinaNeural")
                await communicate.save(voice_path)
                
                # Ovozni yuboramiz
                await message.answer_voice(types.FSInputFile(voice_path))
                if os.path.exists(voice_path): os.remove(voice_path)
                await asyncio.sleep(1) # Server qizib ketmasligi uchun qisqa pauza
                
    except Exception as e:
        await message.answer(f"Hisobotda xatolik: {str(e)}")
    finally:
        await state.clear()
        #start bosganda barcha yozganlarimiz esda qoladi
@dp.message(F.text & ~Command(commands=["start", "mock_ielts"]))
async def chat_with_ai(message: types.Message):
    user_id = message.from_user.id
    
    # Agar foydalanuvchi birinchi marta yozayotgan bo'lsa, tarixni boshlaymiz
    if user_id not in user_histories:
        user_histories[user_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    # Foydalanuvchi xabarini tarixga qo'shamiz
    user_histories[user_id].append({"role": "user", "content": message.text})
    
    # Tarix juda uzayib ketmasligi uchun (masalan oxirgi 10 ta xabar)
    if len(user_histories[user_id]) > 11:
        user_histories[user_id] = [user_histories[user_id][0]] + user_histories[user_id][-10:]

    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    try:
        chat_completion = ai_client.chat.completions.create(
            messages=user_histories[user_id],
            model="llama-3.3-70b-versatile",
        )
        ai_response = chat_completion.choices[0].message.content
        
        # AI javobini ham tarixga qo'shamiz
        user_histories[user_id].append({"role": "assistant", "content": ai_response})
        
        await message.answer(ai_response)
    except Exception as e:
        await message.answer(f"Xatolik: {str(e)}")

# --- STANDART REJIM (OVOZLI CHAT) ---
@dp.message(F.voice)
async def handle_normal_voice(message: types.Message):
    await bot.send_chat_action(chat_id=message.chat.id, action="record_voice")
    user_text = await transcribe_voice(message)
    if not user_text: return
    
    try:
        chat_completion = ai_client.chat.completions.create(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_text}
            ],
            model="llama-3.3-70b-versatile",
        )
        ai_response = chat_completion.choices[0].message.content
        
        voice_model = "uz-UZ-MadinaNeural"
        if any(word in user_text.lower() for word in ['hello', 'what', 'is', 'your', 'name']):
            voice_model = "en-US-EmmaNeural"
            
        reply_voice_path = f"reply_{message.voice.file_id}.mp3"
        communicate = edge_tts.Communicate(ai_response, voice_model)
        await communicate.save(reply_voice_path)
        
        voice_file = types.FSInputFile(reply_voice_path)
        await message.answer_voice(voice_file, caption=f"✍️ <i>Siz aytdingiz: {user_text}</i>", parse_mode="HTML")
        if os.path.exists(reply_voice_path): os.remove(reply_voice_path)
    except Exception as e:
        await message.answer(f"Xatolik: {str(e)}")

async def handle_webhook(request):
    try:
        request_data = await request.json()
        update = types.Update(**request_data)
        await dp.feed_update(bot, update)
        return web.Response(text="OK")
    except Exception as e:
        print(f"Webhook xatosi: {e}")
        return web.Response(text="Error", status=500)

async def on_startup(app):
    await bot.set_webhook(f"{WEBHOOK_URL}/webhook")

def main():
    app = web.Application()
    app.router.add_post("/webhook", handle_webhook)
    app.on_startup.append(on_startup)
    web.run_app(app, host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    main()
