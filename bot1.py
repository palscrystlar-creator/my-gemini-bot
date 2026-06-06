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

# Server va Bot sozlamalari
BOT_TOKEN = "8799568905:AAGY-PYkbve9LkNp2Fy922FAibTopmomu5s"
GROQ_API_KEY = "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"
WEBHOOK_URL = "https://my-gemini-bot-1-14qh.onrender.com"
PORT = int(os.environ.get("PORT", 8080))

# FSM (Holatlar) uchun xotira ombori
storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage)
ai_client = Groq(api_key=GROQ_API_KEY)

# Mock imtihon uchun holat klassi
class MockState(StatesGroup):
    waiting_for_answer = State()

# Tizim qoidalari
SYSTEM_PROMPT = (
    "Sizning ismingiz 'ShavkatoV AI'. "
    "QAT'IY QOIDA: Foydalanuvchi qaysi tilda gapirsa, faqat va faqat o'sha tilning o'zida javob bering. "
    "Agar foydalanuvchi o'zbekcha gapirsa, unga faqat toza o'zbek tilida javob qaytaring va inglizcha tarjimalarni mutloq qo'shmang. "
    "Agar foydalanuvchi inglizcha yozsa - faqat toza inglizcha, ruscha yozsa - faqat toza ruscha javob bering."
)

MOCK_EXAM_PROMPT = (
    "Siz professional ingliz tili imtihon oluvchisiz. Foydalanuvchiga ingliz tili darajasini (Grammar, Vocabulary yoki IELTS) "
    "aniqlash uchun bitta qiziqarli va aniq savol bering. Savolni faqat ingliz tilida yozing."
)

@dp.message(CommandStart())
async def start_command(message: types.Message):
    random_sticker = random.choice(["🚀", "🤖", "🎯", "🌟", "⚡️"])
    welcome_text = (
        f"<b>Salom, {message.from_user.full_name}!</b> 👋\n\n"
        f"🤖 Men <b>ShavkatoV AI</b> botiman.\n"
        f"🎙 Menga yozishingiz yoki ovozli xabar yuborishingiz mumkin!\n\n"
        f"📝 <b>Ingliz tilidan Mock imtihon topshirish uchun:</b> /mock buyrug'ini yuboring!"
    )
    await message.answer(f"{random_sticker} {random_sticker} {random_sticker}")
    await message.answer(welcome_text, parse_mode="HTML")

# --- MOCK IMTIHON FUNKSIYASI (START) ---
@dp.message(Command("mock"))
async def start_mock_exam(message: types.Message, state: FSMContext):
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    try:
        # AI dan yangi inglizcha savol olamiz
        chat_completion = ai_client.chat.completions.create(
            messages=[{"role": "system", "content": MOCK_EXAM_PROMPT}],
            model="llama-3.3-70b-versatile",
        )
        question = chat_completion.choices[0].message.content
        
        # Savolni foydalanuvchiga yuboramiz va uning javobini kutish holatiga o'tamiz
        await message.answer(f"📝 <b>Mock English Exam Question:</b>\n\n{question}\n\n<i>✍️ Please reply to this message with your answer in English.</i>", parse_mode="HTML")
        
        # Foydalanuvchini imtihon holatiga o'tkazamiz va savolni xotirada saqlaymiz
        await state.set_state(MockState.waiting_for_answer)
        await state.update_data(current_question=question)
        
    except Exception as e:
        await message.answer(f"Mock imtihonni boshlashda xatolik: {str(e)}")

# --- MOCK IMTIHON JAVOBINI TEKSHIRISH ---
@dp.message(MockState.waiting_for_answer)
async def check_mock_answer(message: types.Message, state: FSMContext):
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    # Xotiradan berilgan savolni o'qiymiz
    user_data = await state.get_data()
    question = user_data.get("current_question")
    user_answer = message.text
    
    try:
        # AI ga savol va foydalanuvchi javobini tekshirish uchun yuboramiz
        evaluation_prompt = (
            f"You are an English examiner. Check the user's answer based on the question provided.\n"
            f"Question: {question}\n"
            f"User's Answer: {user_answer}\n\n"
            f"Provide a clear feedback in O'zbek tilida (Uzbek). Point out grammar or vocabulary mistakes if any, "
            f"and give a score out of 10 (e.g., Score: 8/10). Keep the explanation encouraging and clear."
        )
        
        chat_completion = ai_client.chat.completions.create(
            messages=[{"role": "user", "content": evaluation_prompt}],
            model="llama-3.3-70b-versatile",
        )
        feedback = chat_completion.choices[0].message.content
        
        # Natijani foydalanuvchiga yuboramiz
        await message.answer(f"📊 <b>Imtihon Natijasi va Tahlil:</b>\n\n{feedback}", parse_mode="HTML")
        
        # Imtihon holatini yakunlaymiz (bot oddiy rejimga qaytadi)
        await state.clear()
        await message.answer("✨ Mock test yakunlandi. Oddiy suhbat rejimiga qaytdingiz. Yana qatnashish uchun /mock yozing.")
        
    except Exception as e:
        await message.answer(f"Javobni tekshirishda xatolik: {str(e)}")
        await state.clear()

# --- OVOZLI XABARLARNI QABUL QILISH ---
@dp.message(F.voice)
async def handle_voice_message(message: types.Message, state: FSMContext):
    # Agar foydalanuvchi imtihon topshirayotgan bo'lsa, ovozli xabar qabul qilmaymiz
    current_state = await state.get_state()
    if current_state == MockState.waiting_for_answer.state:
        await message.answer("Iltimos, mock test savoliga matn ko'rinishida javob yozing. ✍️")
        return

    await bot.send_chat_action(chat_id=message.chat.id, action="record_voice")
    voice_id = message.voice.file_id
    file = await bot.get_file(voice_id)
    file_path = file.file_path
    
    local_voice_path = f"{voice_id}.ogg"
    await bot.download_file(file_path, local_voice_path)
    
    try:
        with open(local_voice_path, "rb") as audio_file:
            transcription = ai_client.audio.transcriptions.create(
                file=(local_voice_path, audio_file.read()),
                model="whisper-large-v3",
            )
        
        user_text = transcription.text
        if not user_text:
            await message.answer("Kechirasiz, ovozingizni tushunolmadim. Qaytadan yozib ko'ring.")
            return

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
            
        reply_voice_path = f"reply_{voice_id}.mp3"
        communicate = edge_tts.Communicate(ai_response, voice_model)
        await communicate.save(reply_voice_path)

        voice_file = types.FSInputFile(reply_voice_path)
        await message.answer_voice(voice_file, caption=f"✍️ <i>Siz aytdingiz: {user_text}</i>", parse_mode="HTML")
        
        if os.path.exists(reply_voice_path): os.remove(reply_voice_path)

    except Exception as e:
        await message.answer(f"Ovozli xabarni qayta ishlashda xatolik: {str(e)}")
    finally:
        if os.path.exists(local_voice_path): os.remove(local_voice_path)

# --- MATNLI XABARLAR ---
@dp.message(F.text)
async def chat_with_ai(message: types.Message):
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    try:
        chat_completion = ai_client.chat.completions.create(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": message.text}
            ],
            model="llama-3.3-70b-versatile",
        )
        await message.answer(chat_completion.choices[0].message.content)
    except Exception as e:
        await message.answer(f"Xatolik yuz berdi: {str(e)}")

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
