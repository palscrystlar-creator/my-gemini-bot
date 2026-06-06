import os
import asyncio
import uuid
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web
from groq import Groq
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
ai_client = Groq(api_key=GROQ_API_KEY)

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

async def send_examiner_voice(message: types.Message, text: str, voice="en-US-BrianNeural"):
    reply_voice_path = f"examiner_{message.chat.id}.mp3"
    try:
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(reply_voice_path)
        await message.answer_voice(types.FSInputFile(reply_voice_path))
    except Exception as e:
        await message.answer(f"[Voice Error] {text}")
    finally:
        if os.path.exists(reply_voice_path):
            try: os.remove(reply_voice_path)
            except: pass

@dp.message(CommandStart())
async def start_command(message: types.Message):
    # WebApp URL manzilini aniqlash (index.html sahifamiz uchun)
    webapp_url = f"{WEBHOOK_URL}/"
    
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="📞 Live AI Call", web_app=types.WebAppInfo(url=webapp_url))]
        ],
        resize_keyboard=True
    )
    
    welcome_text = (
        f"<b>Assalomu alaykum, {message.from_user.full_name}!</b> 👋\n\n"
        f"🤖 Men <b>ShavkatoV AI</b> — sizning shaxsiy ingliz tili treneringizman.\n\n"
        f"📱 <b>YANGILIK:</b> Pastdagi <b>'📞 Live AI Call'</b> tugmasini bosib, men bilan xuddi telefonda gaplashgandek jonli ovozli aloqaga chiqishingiz mumkin!\n\n"
        f"Eski rejimlar: /mock_ielts va /practice"
    )
    await message.answer(welcome_text, reply_markup=keyboard, parse_mode="HTML")

async def transcribe_voice(message: types.Message) -> str:
    voice_id = message.voice.file_id
    file = await bot.get_file(voice_id)
    local_voice_path = f"{voice_id}.ogg"
    await bot.download_file(file.file_path, local_voice_path)
    try:
        with open(local_voice_path, "rb") as audio_file:
            transcription = ai_client.audio.transcriptions.create(
                file=(local_voice_path, audio_file.read()), model="whisper-large-v3"
            )
        return transcription.text
    except: return ""
    finally:
        if os.path.exists(local_voice_path):
            try: os.remove(local_voice_path)
            except: pass

# --- OLDIN YOZILGAN PRACTICE VA IELTS MODULLARI (O'ZGARMADI) ---
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
    await callback.message.answer(f"🚀 Suhbat boshlandi! (Voice: {ai_voice}, Level: {level}, Topic: {topic})")
    
    custom_prompt = f"You are an English partner. Topic: {topic}. Level: {level}. Keep it short (max 2 sentences) and ask a question."
    completion = ai_client.chat.completions.create(
        messages=[{"role": "system", "content": custom_prompt}, {"role": "user", "content": "Start conversation"}],
        model="llama-3.3-70b-versatile"
    )
    first_q = completion.choices[0].message.content
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
    completion = ai_client.chat.completions.create(messages=history, model="llama-3.3-70b-versatile")
    ai_response = completion.choices[0].message.content
    await message.answer(f"✍️ <i>You: {user_text}</i>\n\n💬 <b>AI:</b> {ai_response}", parse_mode="HTML")
    await send_examiner_voice(message, ai_response, voice=ai_voice)
    history.append({"role": "assistant", "content": ai_response})
    await state.update_data(practice_history=history)

@dp.message(Command("stop"))
async def stop_cmd(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("🏁 Suhbat yakunlandi.")

# ==================== WEBAPP LIVE CALL API REJIMI (YANGI) ====================

async def serve_index(request):
    """ index.html faylini WebApp ekraniga chiqarish funksiyasi """
    return web.FileResponse('index.html')

async def handle_voice_call_api(request):
    """ Telefon ekranidan kelgan jonli ovozni qayta ishlash """
    try:
        data = await request.post()
        audio_file = data['audio']
        user_id = data.get('user_id', 'unknown')
        
        # Kelgan ovozni vaqtinchalik saqlash
        temp_webm = f"static/temp_{user_id}.webm"
        temp_wav = f"static/temp_{user_id}.wav"
        
        with open(temp_webm, 'wb') as f:
            f.write(audio_file.file.read())
            
        # WebM formatini Whisper tushunadigan WAV formatiga o'tkazish
        audio = AudioSegment.from_file(temp_webm)
        audio.export(temp_wav, format="wav")
        
        # 1. Whisper yordamida matnga o'girish
        with open(temp_wav, "rb") as f:
            transcription = ai_client.audio.transcriptions.create(
                file=(temp_wav, f.read()), model="whisper-large-v3"
            )
        user_text = transcription.text
        
        # 2. Llama AI orqali tezkor javob tayyorlash
        call_prompt = "You are having a real-time voice call with the user. Keep your response very short, maximum 2 sentences. Speak like a friend."
        completion = ai_client.chat.completions.create(
            messages=[{"role": "system", "content": call_prompt}, {"role": "user", "content": user_text}],
            model="llama-3.3-70b-versatile"
        )
        ai_response = completion.choices[0].message.content
        
        # 3. Edge-TTS yordamida javobni ovoz (mp3) qilish
        response_filename = f"static/res_{uuid.uuid4().hex}.mp3"
        communicate = edge_tts.Communicate(ai_response, "en-US-EmmaNeural")
        await communicate.save(response_filename)
        
        # Vaqtinchalik fayllarni o'chirish
        for f_path in [temp_webm, temp_wav]:
            if os.path.exists(f_path): os.remove(f_path)
            
        # Telefonga audio linkini qaytarish
        audio_url = f"{WEBHOOK_URL}/{response_filename}"
        return web.json_response({"status": "success", "audio_url": audio_url, "text": ai_response})
        
    except Exception as e:
        return web.json_response({"status": "error", "message": str(e)}, status=500)

# ==================== SERVER ISHGA TUSHISHI ====================

async def handle_webhook(request):
    request_data = await request.json()
    update = types.Update(**request_data)
    await dp.feed_update(bot, update)
    return web.Response(text="OK")

async def on_startup(app):
    await bot.set_webhook(f"{WEBHOOK_URL}/webhook")

def main():
    app = web.Application()
    # WebApp va API yo'llari
    app.router.add_get('/', serve_index)
    app.router.add_post('/api/voice-call', handle_voice_call_api)
    app.router.add_post('/webhook', handle_webhook)
    # Statik fayllar (javob audiolari) uchun ruxsat
    app.router.add_static('/static/', path='static', name='static')
    
    app.on_startup.append(on_startup)
    web.run_app(app, host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    main()
