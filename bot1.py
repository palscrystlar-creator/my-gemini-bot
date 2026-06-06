import os
import asyncio
import uuid
import random
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web, ClientSession
import edge_tts

# Server va Bot sozlamalari
BOT_TOKEN = "8799568905:AAGY-PYkbve9LkNp2Fy922FAibTopmomu5s"
GROQ_API_KEY = "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"
WEBHOOK_URL = "https://my-gemini-bot-1-14qh.onrender.com"
PORT = int(os.environ.get("PORT", 8080))

storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage)

# Statik audio fayllar uchun papka ochish
os.makedirs("static", exist_ok=True)

# IELTS Mock Holatlari
class IELTSMockState(StatesGroup):
    part1_q1 = State()
    part1_q2 = State()
    part1_q3 = State()
    part2_cue = State()
    part3_q1 = State()
    part3_q2 = State()
    part3_q3 = State()

# Erkin Amaliyot (Practice) Bosqichlari
class PracticeState(StatesGroup):
    choosing_ai = State()
    choosing_level = State()
    choosing_topic = State()
    speaking = State()

# Tizim qoidalari
SYSTEM_PROMPT = (
    "Sizning ismingiz 'ShavkatoV AI'. Foydalanuvchi qaysi tilda gapirsa, faqat o'sha tilda javob bering. "
    "Agar o'zbekcha gapirsa, faqat toza o'zbekcha javob qaytaring."
)

EXAMINER_PROMPT = (
    "You are an expert IELTS Speaking Examiner. Your tone should be professional, polite, and strict. "
    "Ask only ONE clear question at a time according to the part requirements. Do not output anything else."
)

# ==================== GROQ DIRECT HTTP API FUNCTIONS ====================

async def groq_chat_completion(messages, model="llama-3.3-70b-versatile"):
    """ Groq API bilan to'g'ridan-to'g'ri HTTP Chat muloqoti (groq kutubxonasiz) """
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {"model": model, "messages": messages}
    async with ClientSession() as session:
        async with session.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload) as resp:
            result = await resp.json()
            return result["choices"][0]["message"]["content"]

async def groq_transcribe_audio(file_path):
    """ Groq Whisper API orqali ovozni matnga o'girish (FFmpeg talab qilmaydi) """
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
    data = web.FormData()
    data.add_field('file', open(file_path, 'rb'), filename=os.path.basename(file_path))
    data.add_field('model', 'whisper-large-v3')
    async with ClientSession() as session:
        async with session.post("https://api.groq.com/openai/v1/audio/transcriptions", headers=headers, data=data) as resp:
            result = await resp.json()
            return result.get("text", "")

# Ovoz yuborish umumiy funksiyasi
async def send_examiner_voice(message: types.Message, text: str, voice="en-US-BrianNeural"):
    reply_voice_path = f"static/examiner_{message.chat.id}_{uuid.uuid4().hex}.mp3"
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
        f"<b>Assalomu alaykum, {message.from_user.full_name}!</b> 👋\n\n"
        f"🤖 Men <b>ShavkatoV AI</b> — sizning shaxsiy ingliz tili treneringizman.\n\n"
        f"💡 <b>`MUHIM YO'RIQNOMA:`</b>\n"
        f"Botda ikkita asosiy rejim mavjud:\n"
        f"1️⃣ 🏆 <b>/mock_ielts</b> — To'liq 3 ta qismdan iborat IELTS imtihoni va Band Score.\n"
        f"2️⃣ 🗣 <b>/practice</b> — AI turi, darajangiz va mavzuni tanlab erkin muloqot qilish.\n\n"
        f"<i>Iltimos, bot savollariga faqat <b>OVOZLI XABAR</b> orqali javob bering!</i>"
    )
    await message.answer(welcome_text, parse_mode="HTML")

async def transcribe_voice(message: types.Message) -> str:
    voice_id = message.voice.file_id
    file = await bot.get_file(voice_id)
    local_voice_path = f"{voice_id}.ogg"
    await bot.download_file(file.file_path, local_voice_path)
    try:
        text = await groq_transcribe_audio(local_voice_path)
        return text
    except:
        return ""
    finally:
        if os.path.exists(local_voice_path): 
            try: os.remove(local_voice_path)
            except: pass

# ==================== MUKAMMAL PRACTICE REJIMI ====================

@dp.message(Command("practice"))
async def start_practice(message: types.Message, state: FSMContext):
    await state.clear()
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="👨‍💼 Mr. Brian (Strict & British)", callback_data="ai_en-GB-RyanNeural")],
        [types.InlineKeyboardButton(text="👩‍💼 Miss. Emma (Friendly & American)", callback_data="ai_en-US-EmmaNeural")],
        [types.InlineKeyboardButton(text="❌ Bekor qilish", callback_data="stop_practice")]
    ])
    await message.answer("🤖 <b>1-Bosqich: AI Suhbatdoshingizni tanlang:</b>\nKim bilan suhbatlashishni xohlaysiz?", reply_markup=keyboard, parse_mode="HTML")
    await state.set_state(PracticeState.choosing_ai)

@dp.callback_query(F.data.startswith("ai_"))
async def ai_selected(callback: types.CallbackQuery, state: FSMContext):
    selected_ai = callback.data.split("_")[1]
    await state.update_data(chosen_ai=selected_ai)
    await callback.answer()

    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="🟢 Beginner (A1-A2)", callback_data="lvl_Beginner")],
        [types.InlineKeyboardButton(text="🟡 Intermediate (B1-B2)", callback_data="lvl_Intermediate")],
        [types.InlineKeyboardButton(text="🔴 Advanced (C1-C2)", callback_data="lvl_Advanced")],
        [types.InlineKeyboardButton(text="❌ Bekor qilish", callback_data="stop_practice")]
    ])
    await callback.message.edit_text("📊 <b>2-Bosqich: Ingliz tili darajangizni tanlang:</b>\nAI qanday darajada savol bersin?", reply_markup=keyboard, parse_mode="HTML")
    await state.set_state(PracticeState.choosing_level)

@dp.callback_query(F.data.startswith("lvl_"))
async def level_selected(callback: types.CallbackQuery, state: FSMContext):
    selected_level = callback.data.split("_")[1]
    await state.update_data(chosen_level=selected_level)
    await callback.answer()

    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="📱 Technology & AI", callback_data="prctopic_Technology")],
        [types.InlineKeyboardButton(text="✈️ Travel & Hobbies", callback_data="prctopic_Travel")],
        [types.InlineKeyboardButton(text="🍔 Food & Daily Life", callback_data="prctopic_Food")],
        [types.InlineKeyboardButton(text="🎓 Education & Career", callback_data="prctopic_Education")],
        [types.InlineKeyboardButton(text="❌ Suhbati yakunlash", callback_data="stop_practice")]
    ])
    await callback.message.edit_text("📱 <b>3-Bosqich: Suhbat mavzusini tanlang:</b>\nQaysi mavzu atrofida gaplashamiz?", reply_markup=keyboard, parse_mode="HTML")
    await state.set_state(PracticeState.choosing_topic)

@dp.callback_query(F.data.startswith("prctopic_"))
async def topic_selected(callback: types.CallbackQuery, state: FSMContext):
    topic = callback.data.split("_")[1]
    await callback.answer()
    
    data = await state.get_data()
    ai_voice = data.get("chosen_ai")
    level = data.get("chosen_level")
    
    await callback.message.delete()
    await callback.message.answer(f"🚀 <b>Suhbat boshlandi!</b>\n"
                                  f"👤 <b>AI Ovoz:</b> {'Brian' if 'Ryan' in ai_voice else 'Emma'}\n"
                                  f"📊 <b>Daraja:</b> {level}\n"
                                  f"📱 <b>Mavzu:</b> {topic}\n\n"
                                  f"<i>Menga faqat <b>ovozli xabar</b> yuboring. /stop orqali tugating.</i>", parse_mode="HTML")
    
    custom_prompt = (
        f"You are a friendly English conversation partner. The user wants to practice speaking on the topic '{topic}'. "
        f"The user's English level is {level}. Respond warmly, keep your response under 3 sentences, and ask ONE interesting question."
    )
    
    try:
        first_question = await groq_chat_completion([
            {"role": "system", "content": custom_prompt},
            {"role": "user", "content": f"Start the conversation about {topic}."}
        ])
        
        await callback.message.answer(f"💬 <b>AI:</b> {first_question}")
        await send_examiner_voice(callback.message, first_question, voice=ai_voice)
        
        await state.update_data(practice_prompt=custom_prompt, chosen_ai=ai_voice, practice_history=[
            {"role": "system", "content": custom_prompt},
            {"role": "assistant", "content": first_question}
        ])
        await state.set_state(PracticeState.speaking)
    except Exception as e:
        await callback.message.answer(f"Xatolik: {str(e)}")

@dp.message(PracticeState.speaking, F.voice)
async def handle_practice_voice(message: types.Message, state: FSMContext):
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    user_text = await transcribe_voice(message)
    if not user_text:
        await message.answer("I couldn't catch that. Could you please say it again?")
        return
    
    data = await state.get_data()
    history = data.get("practice_history", [])
    ai_voice = data.get("chosen_ai")
    history.append({"role": "user", "content": user_text})
    
    try:
        ai_response = await groq_chat_completion(history)
        await message.answer(f"✍️ <i>You said: {user_text}</i>\n\n💬 <b>AI:</b> {ai_response}", parse_mode="HTML")
        await send_examiner_voice(message, ai_response, voice=ai_voice)
        
        history.append({"role": "assistant", "content": ai_response})
        await state.update_data(practice_history=history)
    except Exception as e:
        await message.answer(f"Xatolik: {str(e)}")

@dp.message(Command("stop"), PracticeState.speaking)
async def stop_practice_cmd(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("🏁 Erkin suhbat yakunlandi. Oddiy rejimga qaytdingiz. Rahmat!")

@dp.callback_query(F.data == "stop_practice")
async def stop_practice_callback(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()
    await callback.message.edit_text("🏁 Erkin suhbat bekor qilindi.")

# ==================== IELTS SPEAKING MOCK EXAM ====================

@dp.message(Command("mock_ielts"))
async def start_ielts_mock(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("🎬 <b>Welcome to the Full IELTS Speaking Mock Test!</b>\nPlease reply to every question using <b>VOICE MESSAGES</b>.🎙\n\n<i>Starting Part 1...</i>", parse_mode="HTML")
    try:
        q1 = await groq_chat_completion([
            {"role": "system", "content": EXAMINER_PROMPT},
            {"role": "user", "content": "Generate a common IELTS Speaking Part 1 topic question. Ask just one question."}
        ])
        await message.answer(f"🗣 <b>Part 1 - Question 1:</b>\n{q1}", parse_mode="HTML")
        await send_examiner_voice(message, q1)
        await state.set_state(IELTSMockState.part1_q1)
        await state.update_data(p1_q1=q1, history=[])
    except Exception as e:
        await message.answer(f"Xatolik: {str(e)}")

@dp.message(IELTSMockState.part1_q1, F.voice)
async def p1_q1_handler(message: types.Message, state: FSMContext):
    text = await transcribe_voice(message)
    if not text: return
    data = await state.get_data()
    history = data.get("history", [])
    history.append({"role": "user", "content": f"Examiner: {data.get('p1_q1')} | Candidate: {text}"})
    
    q2 = await groq_chat_completion([
        {"role": "system", "content": EXAMINER_PROMPT},
        {"role": "user", "content": f"Ask the second follow-up question for Part 1 based on: {history}"}
    ])
    await message.answer(f"🗣 <b>Part 1 - Question 2:</b>\n{q2}", parse_mode="HTML")
    await send_examiner_voice(message, q2)
    await state.update_data(p1_q2=q2, history=history)
    await state.set_state(IELTSMockState.part1_q2)

@dp.message(IELTSMockState.part1_q2, F.voice)
async def p1_q2_handler(message: types.Message, state: FSMContext):
    text = await transcribe_voice(message)
    if not text: return
    data = await state.get_data()
    history = data.get("history")
    history.append({"role": "user", "content": f"Examiner: {data.get('p1_q2')} | Candidate: {text}"})
    
    q3 = await groq_chat_completion([
        {"role": "system", "content": EXAMINER_PROMPT},
        {"role": "user", "content": f"Ask the third question for Part 1 based on: {history}"}
    ])
    await message.answer(f"🗣 <b>Part 1 - Question 3:</b>\n{q3}", parse_mode="HTML")
    await send_examiner_voice(message, q3)
    await state.update_data(p1_q3=q3, history=history)
    await state.set_state(IELTSMockState.part1_q3)

@dp.message(IELTSMockState.part1_q3, F.voice)
async def p1_q3_handler(message: types.Message, state: FSMContext):
    text = await transcribe_voice(message)
    if not text: return
    data = await state.get_data()
    history = data.get("history")
    history.append({"role": "user", "content": f"Examiner: {data.get('p1_q3')} | Candidate: {text}"})
    
    await message.answer(" Moving to <b>Part 2 (Cue Card)</b>.", parse_mode="HTML")
    cue_card = await groq_chat_completion([
        {"role": "system", "content": "You are an IELTS examiner. Provide a complete IELTS Speaking Part 2 Cue Card task block."}
    ])
    await message.answer(f"📋 <b>PART 2 - CUE CARD:</b>\n\n{cue_card}\n\n<i>🔴 Please record your voice now (1-2 minutes).</i>", parse_mode="HTML")
    await send_examiner_voice(message, "Please look at the cue card on your screen. Start your voice message whenever you are ready.")
    await state.update_data(p2_cue=cue_card, history=history)
    await state.set_state(IELTSMockState.part2_cue)

@dp.message(IELTSMockState.part2_cue, F.voice)
async def p2_handler(message: types.Message, state: FSMContext):
    text = await transcribe_voice(message)
    if not text: return
    data = await state.get_data()
    history = data.get("history")
    history.append({"role": "user", "content": f"Part 2 Cue Card: {data.get('p2_cue')} | Candidate Response: {text}"})
    
    await message.answer(" Proceeding to <b>Part 3 (Discussion)</b>.", parse_mode="HTML")
    p3_q1 = await groq_chat_completion([
        {"role": "system", "content": EXAMINER_PROMPT},
        {"role": "user", "content": f"Ask the first deep question for Part 3 based on Part 2 topic."}
    ])
    await message.answer(f"🗣 <b>Part 3 - Question 1:</b>\n{p3_q1}", parse_mode="HTML")
    await send_examiner_voice(message, p3_q1)
    await state.update_data(p3_q1=p3_q1, history=history)
    await state.set_state(IELTSMockState.part3_q1)

@dp.message(IELTSMockState.part3_q1, F.voice)
async def p3_q1_handler(message: types.Message, state: FSMContext):
    text = await transcribe_voice(message)
    if not text: return
    data = await state.get_data()
    history = data.get("history")
    history.append({"role": "user", "content": f"Examiner: {data.get('p3_q1')} | Candidate: {text}"})
    
    p3_q2 = await groq_chat_completion([
        {"role": "system", "content": EXAMINER_PROMPT},
        {"role": "user", "content": f"Ask the second Part 3 question based on: {history}"}
    ])
    await message.answer(f"🗣 <b>Part 3 - Question 2:</b>\n{p3_q2}", parse_mode="HTML")
    await send_examiner_voice(message, p3_q2)
    await state.update_data(p3_q2=p3_q2, history=history)
    await state.set_state(IELTSMockState.part3_q2)

@dp.message(IELTSMockState.part3_q2, F.voice)
async def p3_q2_handler(message: types.Message, state: FSMContext):
    text = await transcribe_voice(message)
    if not text: return
    data = await state.get_data()
    history = data.get("history")
    history.append({"role": "user", "content": f"Examiner: {data.get('p3_q2')} | Candidate: {text}"})
    
    p3_q3 = await groq_chat_completion([
        {"role": "system", "content": EXAMINER_PROMPT},
        {"role": "user", "content": f"Ask the third question for Part 3 based on: {history}"}
    ])
    await message.answer(f"🗣 <b>Part 3 - Question 3 (Final):</b>\n{p3_q3}", parse_mode="HTML")
    await send_examiner_voice(message, p3_q3)
    await state.update_data(p3_q3=p3_q3, history=history)
    await state.set_state(IELTSMockState.part3_q3)

@dp.message(IELTSMockState.part3_q3, F.voice)
async def p3_q3_handler(message: types.Message, state: FSMContext):
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    await message.answer("🏁 <i>Test tugadi! Tahlil qilinmoqda, iltimos kuting...</i>")
    text = await transcribe_voice(message)
    if not text: return
    data = await state.get_data()
    history = data.get("history")
    history.append({"role": "user", "content": f"Examiner: {data.get('p3_q3')} | Candidate: {text}"})
    
    try:
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
        report_content = await groq_chat_completion([{"role": "user", "content": report_prompt}])
        sections = report_content.split("---")
        
        await message.answer("📊 <b>SIZNING TO'LIQ IELTS MOCK HISOBOTINGIZ:</b>")
        for index, section in enumerate(sections):
            clean_section = section.strip()
            if clean_section:
                await message.answer(clean_section)
                voice_path = f"static/report_part_{index}_{message.chat.id}.mp3"
                communicate = edge_tts.Communicate(clean_section.replace("**", "").replace("*", ""), "uz-UZ-MadinaNeural")
                await communicate.save(voice_path)
                await message.answer_voice(types.FSInputFile(voice_path))
                if os.path.exists(voice_path): 
                    try: os.remove(voice_path)
                    except: pass
                await asyncio.sleep(1)
    except Exception as e:
        await message.answer(f"Xatolik: {str(e)}")
    finally:
        await state.clear()

# --- STANDART MATNLI CHAT ---
@dp.message(F.text)
async def chat_with_ai(message: types.Message):
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    try:
        ai_reply = await groq_chat_completion([
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": message.text}
        ])
        await message.answer(ai_reply)
    except Exception as e:
        await message.answer(f"Xatolik: {str(e)}")

# --- STANDART OVOZLI CHAT ---
@dp.message(F.voice)
async def handle_normal_voice(message: types.Message):
    await bot.send_chat_action(chat_id=message.chat.id, action="record_voice")
    user_text = await transcribe_voice(message)
    if not user_text: return
    try:
        ai_response = await groq_chat_completion([
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_text}
        ])
        voice_model = "uz-UZ-MadinaNeural"
        if any(word in user_text.lower() for word in ['hello', 'what', 'is', 'your', 'name']):
            voice_model = "en-US-EmmaNeural"
            
        reply_voice_path = f"static/reply_{message.voice.file_id}.mp3"
        communicate = edge_tts.Communicate(ai_response, voice_model)
        await communicate.save(reply_voice_path)
        await message.answer_voice(types.FSInputFile(reply_voice_path), caption=f"✍️ <i>Siz aytdingiz: {user_text}</i>", parse_mode="HTML")
        if os.path.exists(reply_voice_path): 
            try: os.remove(reply_voice_path)
            except: pass
    except Exception as e:
        await message.answer(f"Xatolik: {str(e)}")

# ==================== WEBHOOK VA STARTUP ====================
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
    bot_commands = [
        types.BotCommand(command="start", description="Botni qayta ishga tushirish 🚀"),
        types.BotCommand(command="mock_ielts", description="IELTS Mock Exam (Full Part 1, 2, 3) 🏆"),
        types.BotCommand(command="practice", description="Erkin mavzularda ovozli suhbat mashqi 🗣")
    ]
    await bot.set_my_commands(bot_commands)

def main():
    app = web.Application()
    app.router.add_post("/webhook", handle_webhook)
    app.on_startup.append(on_startup)
    web.run_app(app, host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    main()
