import os
import asyncio
import random
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiohttp import web
from groq import Groq
from gtts import gTTS

# Server va Bot sozlamalari
BOT_TOKEN = "8799568905:AAGY-PYkbve9LkNp2Fy922FAibTopmomu5s"
GROQ_API_KEY = "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"
WEBHOOK_URL = "https://my-gemini-bot-1-14qh.onrender.com"
PORT = int(os.environ.get("PORT", 8080))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
ai_client = Groq(api_key=GROQ_API_KEY)

# Tizim qoidasi (System Prompt)
SYSTEM_PROMPT = (
    "Sizning ismingiz 'ShavkatoV AI'. "
    "QAT'IY QOIDA: Foydalanuvchi qaysi tilda gapirsa, faqat va faqat o'sha tilning o'zida javob bering. "
    "Agar foydalanuvchi o'zbekcha gapirsa, unga faqat toza o'zbek tilida javob qaytaring va inglizcha tarjimalarni mutloq qo'shmang. "
    "Agar foydalanuvchi inglizcha yozsa - faqat toza inglizcha, ruscha yozsa - faqat toza ruscha javob bering."
)

@dp.message(CommandStart())
async def start_command(message: types.Message):
    random_sticker = random.choice(["🚀", "🤖", "🎯", "🌟", "⚡️"])
    interesting_facts = [
        "Okeandagi eng chuqur joy — Mariana botiqligi bo'lib, uning tubiga tashlangan temir shar pastga yetib borishi uchun 1 soatdan ko'proq vaqt ketadi! 🌊",
        "Asal hech qachon buzilmaydigan yagona mahsulotdir. Misr ehromlaridan topilgan 3000 yillik asal hali ham iste'molga yaroqli ekanligi aniqlangan! 🍯",
        "Ipak qurti bor-yo'g'i 56 kun ichida o'z vaznidan 86 ming marta ko'p ovqat yeydi! 🐛",
        "Dunyodagi eng birinchi dasturchi ayol kishi bo'lgan. Uning ismi Ada Lavleys (Ada Lovelace) edi! 👩‍💻",
        "Inson miyasi uyg'oq paytida bitta kichik lampochkani yoqishga yetadigan miqdorda elektr energiyasi ishlab chiqaradi! 🧠⚡️",
        "Sayyoramizdagi barcha chumolilarning umumiy vazni yer yuzidagi barcha odamlarning vazniga teng keladi! 🐜"
    ]
    random_fact = random.choice(interesting_facts)
    
    await message.answer(f"{random_sticker} {random_sticker} {random_sticker}")
    welcome_text = (
        f"<b>Salom, {message.from_user.full_name}!</b> 👋\n\n"
        f"🤖 Men <b>ShavkatoV AI</b> botiman. Menga yozishingiz yoki <b>ovozli xabar</b> yuborishingiz mumkin! 🎙\n\n"
        f"✨ <b>Siz uchun kunlik qiziqarli fakt:</b>\n"
        f"<i>{random_fact}</i>"
    )
    await message.answer(welcome_text, parse_mode="HTML")

# --- OVOZLI XABARLARNI QABUL QILISH VA JAVOB QAYTARISH ---
@dp.message(F.voice)
async def handle_voice_message(message: types.Message):
    # Bot "ovoz yozib olyapti..." holatiga o'tadi
    await bot.send_chat_action(chat_id=message.chat.id, action="record_voice")
    
    voice_id = message.voice.file_id
    file = await bot.get_file(voice_id)
    file_path = file.file_path
    
    # Ovozli faylni yuklab olamiz
    local_voice_path = f"{voice_id}.ogg"
    await bot.download_file(file_path, local_voice_path)
    
    try:
        # 1. Groq Whisper orqali ovozni matnga o'giramiz
        with open(local_voice_path, "rb") as audio_file:
            transcription = ai_client.audio.transcriptions.create(
                file=(local_voice_path, audio_file.read()),
                model="whisper-large-v3",
            )
        
        user_text = transcription.text
        if not user_text:
            await message.answer("Kechirasiz, ovozingizni eshita olmadim. Qaytadan yozib ko'ring.")
            return

        # 2. Llama 3 AI modelidan javob olamiz
        chat_completion = ai_client.chat.completions.create(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_text}
            ],
            model="llama-3.3-70b-versatile",
        )
        ai_response = chat_completion.choices[0].message.content

        # 3. gTTS orqali AI javobini ovozli faylga (MP3) aylantiramiz
        # Avtomatik tilni aniqlash (o'zbekcha bo'lsa 'uz', inglizcha bo'lsa 'en')
        # gTTS o'zbekchani 'uz' kodi bilan qo'llab-quvvatlaydi
        tts_lang = 'uz'
        if any(word in user_text.lower() for word in ['hello', 'what', 'is', 'your', 'name']):
            tts_lang = 'en'
            
        tts = gTTS(text=ai_response, lang=tts_lang, slow=False)
        reply_voice_path = f"reply_{voice_id}.mp3"
        tts.save(reply_voice_path)

        # 4. Foydalanuvchiga ovozli javobni yuboramiz
        voice_file = types.FSInputFile(reply_voice_path)
        await message.answer_voice(voice_file, caption=f"✍️ <i>Siz aytdingiz: {user_text}</i>", parse_mode="HTML")
        
        # Vaqtinchalik fayllarni tozalaymiz
        if os.path.exists(reply_voice_path): os.remove(reply_voice_path)

    except Exception as e:
        await message.answer(f"Ovozli xabarni qayta ishlashda xatolik: {str(e)}")
    
    finally:
        if os.path.exists(local_voice_path): os.remove(local_voice_path)

# --- MATNLI XABARLAR (Eski holatidek qoladi) ---
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
