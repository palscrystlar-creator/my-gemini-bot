import os
import asyncio
import uuid
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

# --- HOZIRGI STATES (HOLATLAR) ---
class IELTSMockState(StatesGroup):
    part1 = State()
    part2 = State()
    part3 = State()

class PracticeState(StatesGroup):
    choosing_ai = State()
    choosing_level = State()
    choosing_topic = State()
    speaking = State()

# --- BAZAVIY PROMPTLAR ---
SYSTEM_PROMPT = "Siz ShavkatoV AI shaxsiy assistentisiz. Foydalanuvchi tiliga mos javob bering va qisqa gapiring."
IELTS_PROMPT = "You are an expert IELTS Speaking Examiner. Conduct a structured exam (Part 1, Part 2, Part 3). Ask one question at a time. Be strict and professional."

# Groq API bilan to'g'ridan-to'g'ri Chat HTTP so'rovi
async def groq_chat_completion(messages, model="llama-3.3-70b-versatile"):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {"model": model, "messages": messages}
    async with ClientSession() as session:
        async with session.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload) as resp:
            result = await resp.json()
            return result["choices"][0]["message"]["content"]

# Groq API bilan to'g'ridan-to'g'ri Audio Transcribe (Whisper) HTTP so'rovi
async def groq_transcribe_audio(file_path):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
    data = web.FormData()
    data.add_field('file', open(file_path, 'rb'), filename=os.path.basename(file_path))
    data.add_field('model', 'whisper-large-v3')
    async with ClientSession() as session:
        async with session.post("https://api.groq.com/openai/v1/audio/transcriptions", headers=headers, data=data) as resp:
            result = await resp.json()
            return result.get("text", "")

async def send_voice_response(message: types.Message, text: str, voice="en-US-BrianNeural"):
    reply_voice_path = f"static/voice_{uuid.uuid4().hex}.mp3"
    try:
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(reply_voice_path)
        await message.answer_voice(types.FSInputFile(reply_voice_path))
    except:
        await message.answer(f"[Voice Error] {text}")
    finally:
        if os.path.exists(reply_voice_path):
            try: os.remove(reply_voice_path)
            except: pass

# --- START BUYRUG'I ---
@dp.message(CommandStart())
async def start_command(message: types.Message, state: FSMContext):
    await state.clear()
    webapp_url = f"{WEBHOOK_URL}/"
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[[types.KeyboardButton(text="📞 Live AI Call", web_app=types.WebAppInfo(url=webapp_url))]],
        resize_keyboard=True
    )
    welcome_text = (
        f"<b>Assalomu alaykum, {message.from_user.full_name}!</b> 👋\n\n"
        f"🤖 Men <b>ShavkatoV AI</b> — sizning shaxsiy ingliz tili treneringizman.\n\n"
        f"📱 Pastdagi <b>'📞 Live AI Call'</b> tugmasini bosib, men bilan xuddi telefonda gaplashgandek jonli ovozli muloqot qiling!\n\n"
        f"Eski rejimlar:\n"
        f"🏆 /mock_ielts — Imtihon topshirish\n"
        f"🗣 /practice — Erkin mavzularda ovozli suhbat"
    )
    await message.answer(welcome_text, reply_markup=keyboard, parse_mode="HTML")

# ==================== 1. IELTS MOCK EXAM MODULI (YANGI QO'SHILDI) ====================
@dp.message(Command("mock_ielts"))
async def start_mock_ielts(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("🏆 <b>IELTS Speaking Mock Exam boshlandi!</b>\n\n<i>Part 1: Introduction and Interview.</i>\nAI Examiner hozir sizga birinchi savolni beradi. Faqat OVOZLI XABAR (Voice) orqali javob bering.")
    
    first_q = "Welcome to the IELTS Speaking test. Can you tell me your full name, and do you work or study?"
    await message.answer(f"👨‍💼 <b>Examiner:</b> {first_q}")
    await send_voice_response(message, first_q, voice="en-GB-RyanNeural")
    
    await state.update_data(history=[{"role": "system", "content": IELTS_PROMPT}, {"role": "assistant", "content": first_q}], count=1)
    await state.set_state(IELTSMockState.part1)

@dp.message(IELTSMockState.part1, F.voice)
async def handle_ielts_part1(message: types.Message, state: FSMContext):
    voice_id = message.voice.file_id
    file = await bot.get_file(voice_id)
    local_path = f"{voice_id}.ogg"
    await bot.download_file(file.file_path, local_path)
    
    user_text = await groq_transcribe_audio(local_path)
    if os.path.exists(local_path): os.remove(local_path)
    
    if not user_text:
        await message.answer("Ovozingizni yaxshi eshitmadim, iltimos qaytadan yuboring.")
        return

    data = await state.get_data()
    history = data.get("history", [])
    count = data.get("count", 1)
    
    history.append({"role": "user", "content": user_text})
    
    if count < 3:
        # Part 1 savollarini davom ettirish
        ai_q = await groq_chat_completion(history)
        await message.answer(f"✍️ <i>You: {user_text}</i>\n\n👨‍💼 <b>Examiner:</b> {ai_q}")
        await send_voice_response(message, ai_q, voice="en-GB-RyanNeural")
        history.append({"role": "assistant", "content": ai_q})
        await state.update_data(history=history, count=count+1)
    else:
        # Part 2 ga o'tish
        part2_text = "Moving on to Part 2. I will give you a topic. You should talk about it for 1 to 2 minutes. Describe a beautiful place you have visited. You have 1 minute to prepare."
        await message.answer(f"✍️ <i>You: {user_text}</i>\n\n👨‍💼 <b>Examiner (Part 2):</b> {part2_text}")
        await send_voice_response(message, part2_text, voice="en-GB-RyanNeural")
        history.append({"role": "assistant", "content": part2_text})
        await state.update_data(history=history)
        await state.set_state(IELTSMockState.part2)

@dp.message(IELTSMockState.part2, F.voice)
async def handle_ielts_part2(message: types.Message, state: FSMContext):
    # Part 2 javobini qabul qilish va Part 3 ga o'tish
    await message.answer("Thank you. Now let's move to Part 3. I will ask you some discussion questions related to tourism.")
    part3_q = "Why do you think people like to travel to beautiful places?"
    await message.answer(f"👨‍💼 <b>Examiner (Part 3):</b> {part3_q}")
    await send_voice_response(message, part3_q, voice="en-GB-RyanNeural")
    
    data = await state.get_data()
    history = data.get("history", [])
    history.append({"role": "assistant", "content": part3_q})
    await state.update_data(history=history)
    await state.set_state(IELTSMockState.part3)

@dp.message(IELTSMockState.part3, F.voice)
async def handle_ielts_part3(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("🏁 <b>Thank you! The IELTS Speaking Mock Exam is now complete.</b>\n\nSiz imtihonni muvaffaqiyatli yakunladingiz! Real rejimda bu yerda to'liq feedback beriladi.")

# ==================== 2. ERKIN PRACTICE REJIMI ====================
@dp.message(Command("practice"))
async def start_practice(message: types.Message, state: FSMContext):
    await state.clear()
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="👨‍💼 Mr. Brian (British)", callback_data="ai_en-GB-RyanNeural")],
        [types.InlineKeyboardButton(text="👩‍💼 Miss. Emma (American)", callback_data="ai_en-US-EmmaNeural")]
    ])
    await message.answer("🤖 <b>AI Suhbatdoshingizni tanlang:</b>", reply_markup=keyboard, parse_mode="HTML")
    await state.set_state(PracticeState.choosing_ai)

@dp.callback_query(F.data.startswith("ai_"))
async def ai_selected(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(chosen_ai=callback.data.split("_")[1])
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="🟢 Beginner", callback_data="lvl_Beginner")],
        [types.InlineKeyboardButton(text="🟡 Intermediate", callback_data="lvl_Intermediate")],
        [types.InlineKeyboardButton(text="🔴 Advanced", callback_data="lvl_Advanced")]
    ])
    await callback.message.edit_text("📊 <b>Darajangizni tanlang:</b>", reply_markup=keyboard, parse_mode="HTML")
    await state.set_state(PracticeState.choosing_level)

@dp.callback_query(F.data.startswith("lvl_"))
async def level_selected(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(chosen_level=callback.data.split("_")[1])
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="📱 Technology", callback_data="prctopic_Technology")],
        [types.InlineKeyboardButton(text="✈️ Travel", callback_data="prctopic_Travel")]
    ])
    await callback.message.edit_text("📱 <b>Mavzuni tanlang:</b>", reply_markup=keyboard, parse_mode="HTML")
    await state.set_state(PracticeState.choosing_topic)

@dp.callback_query(F.data.startswith("prctopic_"))
async def topic_selected(callback: types.CallbackQuery, state: FSMContext):
    topic = callback.data.split("_")[1]
    data = await state.get_data()
    ai_voice = data.get("chosen_ai")
    level = data.get("chosen_level")
    await callback.message.delete()
    await callback.message.answer(f"🚀 Suhbat boshlandi! (Level: {level}, Topic: {topic}). To'xtatish uchun /stop yozing.")
    
    custom_prompt = f"You are an English partner. Topic: {topic}. Level: {level}. Keep it short (max 2 sentences) and ask a question."
    first_q = await groq_chat_completion([{"role": "system", "content": custom_prompt}, {"role": "user", "content": "Start conversation"}])
    
    await callback.message.answer(f"💬 <b>AI:</b> {first_q}", parse_mode="HTML")
    await send_voice_response(callback.message, first_q, voice=ai_voice)
    await state.update_data(practice_history=[{"role": "system", "content": custom_prompt}, {"role": "assistant", "content": first_q}], chosen_ai=ai_voice)
    await state.set_state(PracticeState.speaking)

@dp.message(PracticeState.speaking, F.voice)
async def handle_practice_voice(message: types.Message, state: FSMContext):
    voice_id = message.voice.file_id
    file = await bot.get_file(voice_id)
    local_path = f"{voice_id}.ogg"
    await bot.download_file(file.file_path, local_path)
    
    user_text = await groq_transcribe_audio(local_path)
    if os.path.exists(local_path): os.remove(local_path)
    
    if not user_text: return
    
    data = await state.get_data()
    history = data.get("practice_history", [])
    ai_voice = data.get("chosen_ai")
    history.append({"role": "user", "content": user_text})
    
    ai_response = await groq_chat_completion(history)
    await message.answer(f"✍️ <i>You: {user_text}</i>\n\n💬 <b>AI:</b> {ai_response}", parse_mode="HTML")
    await send_voice_response(message, ai_response, voice=ai_voice)
    history.append({"role": "assistant", "content": ai_response})
    await state.update_data(practice_history=history)

@dp.message(Command("stop"))
async def stop_cmd(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("🏁 Erkin suhbat yakunlandi.")

# ==================== 3. ODDIY CHAT (SALOM-ALIK REJIMI) ====================
@dp.message(F.text)
async def handle_text_chat(message: types.Message):
    # Agar foydalanuvchi oddiy matn yozsa (masalan: Salom), AI unga matn bilan javob beradi
    ai_reply = await groq_chat_completion([
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": message.text}
    ])
    await message.answer(ai_reply)

# ==================== WEBAPP LIVE CALL API REJIMI ====================
async def serve_index(request):
    return web.FileResponse('index.html')

async def handle_voice_call_api(request):
    try:
        data = await request.post()
        audio_file = data['audio']
        user_id = data.get('user_id', 'unknown')
        temp_webm = f"static/temp_{user_id}.webm"
        with open(temp_webm, 'wb') as f:
            f.write(audio_file.file.read())
        
        user_text = await groq_transcribe_audio(temp_webm)
        call_prompt = "You are having a real-time voice call with the user. Keep your response very short, maximum 2 sentences. Speak like a friend."
        ai_response = await groq_chat_completion([
            {"role": "system", "content": call_prompt},
            {"role": "user", "content": user_text}
        ])
        
        response_filename = f"static/res_{uuid.uuid4().hex}.mp3"
        communicate = edge_tts.Communicate(ai_response, "en-US-EmmaNeural")
        await communicate.save(response_filename)
        
        if os.path.exists(temp_webm): os.remove(temp_webm)
        audio_url = f"{WEBHOOK_URL}/{response_filename}"
        return web.json_response({"status": "success", "audio_url": audio_url, "text": ai_response})
    except Exception as e:
        return web.json_response({"status": "error", "message": str(e)}, status=500)

# ==================== SERVER ENGINE ====================
async def handle_webhook(request):
    request_data = await request.json()
    update = types.Update(**request_data)
    await dp.feed_update(bot, update)
    return web.Response(text="OK")

async def on_startup(app):
    await bot.set_webhook(f"{WEBHOOK_URL}/webhook")

def main():
    app = web.Application()
    app.router.add_get('/', serve_index)
    app.router.add_post('/api/voice-call', handle_voice_call_api)
    app.router.add_post('/webhook', handle_webhook)
    app.router.add_static('/static/', path='static', name='static')
    app.on_startup.append(on_startup)
    web.run_app(app, host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    main()
