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
from pydub import AudioSegment

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

class IELTSMockState(StatesGroup):
    part1_q1, part1_q2, part1_q3 = State(), State(), State()
    part2_cue = State()
    part3_q1, part3_q2, part3_q3 = State(), State(), State()

class PracticeState(StatesGroup):
    choosing_ai = State()
    choosing_level = State()
    choosing_topic = State()
    speaking = State()

SYSTEM_PROMPT = "Siz ShavkatoV AI shaxsiy assistentisiz. Foydalanuvchi tiliga mos javob bering."
EXAMINER_PROMPT = "You are an expert IELTS Speaking Examiner. Ask ONE question at a time. No extra text."

# Groq API bilan to'g'ridan-to'g'ri Chat HTTP so'rovi
async def groq_chat_completion(messages, model="llama-3.3-70b-versatile"):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": messages
    }
    async with ClientSession() as session:
        async with session.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload) as resp:
            result = await resp.json()
            return result["choices"][0]["message"]["content"]

# Groq API bilan to'g'ridan-to'g'ri Audio Transcribe (Whisper) HTTP so'rovi
async def groq_transcribe_audio(file_path):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}"
    }
    data = web.FormData()
    data.add_field('file', open(file_path, 'rb'), filename=os.path.basename(file_path))
    data.add_field('model', 'whisper-large-v3')
    
    async with ClientSession() as session:
        async with session.post("https://api.groq.com/openai/v1/audio/transcriptions", headers=headers, data=data) as resp:
            result = await resp.json()
            return result.get("text", "")

async def send_examiner_voice(message: types.Message, text: str, voice="en-US-BrianNeural"):
    reply_voice_path = f"examiner_{message.chat.id}.mp3"
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

@dp.message(CommandStart())
async def start_command(message: types.Message):
    webapp_url = f"{WEBHOOK_URL}/"
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[[types.KeyboardButton(text="📞 Live AI Call", web_app=types.WebAppInfo(url=webapp_url))]],
        resize_keyboard=True
    )
    welcome_text = (
        f"<b>Assalomu alaykum, {message.from_user.full_name}!</b> 👋\n\n"
        f"🤖 Men <b>ShavkatoV AI</b> — sizning shaxsiy ingliz tili treneringizman.\n\n"
        f"📱 Pastdagi <b>'📞 Live AI Call'</b> tugmasini bosib, men bilan xuddi telefonda gaplashgandek jonli ovozli muloqot qiling!\n\n"
        f"Eski rejimlar: /mock_ielts va /practice"
    )
    await message.answer(welcome_text, reply_markup=keyboard, parse_mode="HTML")

async def transcribe_voice(message: types.Message) -> str:
    voice_id = message.voice.file_id
    file = await bot.get_file(voice_id)
    local_voice_path = f"{voice_id}.ogg"
    await bot.download_file(file.file_path, local_voice_path)
    try:
        # OGG formatini WAV formatiga o'tkazamiz (Whisper yaxshi tushunishi uchun)
        wav_path = f"{voice_id}.wav"
        audio = AudioSegment.from_file(local_voice_path)
        audio.export(wav_path, format="wav")
        
        text = await groq_transcribe_audio(wav_path)
        if os.path.exists(wav_path): os.remove(wav_path)
        return text
    except: return ""
    finally:
        if os.path.exists(local_voice_path): os.remove(local_voice_path)

# --- PRACTICE VA IELTS MODULLARI (HTTP'ga MOSLANDI) ---
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
    await callback.message.answer(f"🚀 Suhbat boshlandi! (Level: {level}, Topic: {topic})")
    
    custom_prompt = f"You are an English partner. Topic: {topic}. Level: {level}. Keep it short (max 2 sentences) and ask a question."
    first_q = await groq_chat_completion([{"role": "system", "content": custom_prompt}, {"role": "user", "content": "Start conversation"}])
    
    await callback.message.answer(f"💬 <b>AI:</b> {first_q}", parse_mode="HTML")
    await send_examiner_voice(callback.message, first_q, voice=ai_voice)
    await state.update_data(practice_history=[{"role": "system", "content": custom_prompt}, {"role": "assistant", "content": first_q}], chosen_ai=ai_voice)
    await state.set_state(PracticeState.speaking)

@dp.message(PracticeState.speaking, F.voice)
async def handle_practice_voice(message: types.Message, state: FSMContext):
    user_text = await transcribe_voice(message)
    if not user_text: return
    data = await state.get_data()
    history = data.get("practice_history", [])
    ai_voice = data.get("chosen_ai")
    history.append({"role": "user", "content": user_text})
    
    ai_response = await groq_chat_completion(history)
    await message.answer(f"✍️ <i>You: {user_text}</i>\n\n💬 <b>AI:</b> {ai_response}", parse_mode="HTML")
    await send_examiner_voice(message, ai_response, voice=ai_voice)
    history.append({"role": "assistant", "content": ai_response})
    await state.update_data(practice_history=history)

@dp.message(Command("stop"))
async def stop_cmd(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("🏁 Suhbat yakunlandi.")

# ==================== WEBAPP LIVE CALL API REJIMI ====================

async def serve_index(request):
    return web.FileResponse('index.html')

async def handle_voice_call_api(request):
    try:
        data = await request.post()
        audio_file = data['audio']
        user_id = data.get('user_id', 'unknown')
        
        temp_webm = f"static/temp_{user_id}.webm"
        temp_wav = f"static/temp_{user_id}.wav"
        
        with open(temp_webm, 'wb') as f:
            f.write(audio_file.file.read())
            
        audio = AudioSegment.from_file(temp_webm)
        audio.export(temp_wav, format="wav")
        
        # 1. To'g'ridan-to'g'ri HTTP orqali Whisper matnga o'girish
        user_text = await groq_transcribe_audio(temp_wav)
        
        # 2. To'g'ridan-to'g'ri HTTP orqali Llama javobi
        call_prompt = "You are having a real-time voice call with the user. Keep your response very short, maximum 2 sentences. Speak like a friend."
        ai_response = await groq_chat_completion([
            {"role": "system", "content": call_prompt},
            {"role": "user", "content": user_text}
        ])
        
        # 3. Ovozga o'tkazish
        response_filename = f"static/res_{uuid.uuid4().hex}.mp3"
        communicate = edge_tts.Communicate(ai_response, "en-US-EmmaNeural")
        await communicate.save(response_filename)
        
        for f_path in [temp_webm, temp_wav]:
            if os.path.exists(f_path): os.remove(f_path)
            
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
