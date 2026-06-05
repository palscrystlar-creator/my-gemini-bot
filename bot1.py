import os
import asyncio
import random  # Tasodifiy faktlar uchun
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiohttp import web
from groq import Groq

# Server va Bot sozlamalari
BOT_TOKEN = "8799568905:AAGY-PYkbve9LkNp2Fy922FAibTopmomu5s"
GROQ_API_KEY = "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"  # Siz bergan haqiqiy kalit joylashtirildi
WEBHOOK_URL = "https://my-gemini-bot-1-14qh.onrender.com"
PORT = int(os.environ.get("PORT", 8080))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
ai_client = Groq(api_key=GROQ_API_KEY)

@dp.message(CommandStart())
async def start_command(message: types.Message):
    # Tasodifiy emojilar
    random_sticker = random.choice(["🚀", "🤖", "🎯", "🌟", "⚡️"])
    
    # Qiziqarli ma'lumotlar ro'yxati
    interesting_facts = [
        "Okeandagi eng chuqur joy — Mariana botiqligi bo'lib, uning tubiga tashlangan temir shar pastga yetib borishi uchun 1 soatdan ko'proq vaqt ketadi! 🌊",
        "Asal hech qachon buzilmaydigan yagona mahsulotdir. Misr ehromlaridan topilgan 3000 yillik asal hali ham iste'molga yaroqli ekanligi aniqlangan! 🍯",
        "Ipak qurti bor-yo'g'i 56 kun ichida o'z vaznidan 86 ming marta ko'p ovqat yeydi! 🐛",
        "Dunyodagi eng birinchi dasturchi ayol kishi bo'lgan. Uning ismi Ada Lavleys (Ada Lovelace) edi! 👩‍💻",
        "Inson miyasi uyg'oq paytida bitta kichik lampochkani yoqishga yetadigan miqdorda elektr energiyasi ishlab chiqaradi! 🧠⚡️",
        "Sayyoramizdagi barcha chumolilarning umumiy vazni yer yuzidagi barcha odamlarning vazniga teng keladi! 🐜"
    ]
    random_fact = random.choice(interesting_facts)
    
    # Birinchi bo'lib emojilar ketadi
    await message.answer(f"{random_sticker} {random_sticker} {random_sticker}")
    
    # HTML formatidagi chiroyli salomlashish matni
    welcome_text = (
        f"<b>Salom, {message.from_user.full_name}!</b> 👋\n\n"
        f"🤖 Men <b>ShavkatoV AI</b> botiman. Menga istalgan mavzuda savol berishingiz mumkin!\n\n"
        f"✨ <b>Siz uchun kunlik qiziqarli fakt:</b>\n"
        f"<i>{random_fact}</i>"
    )
    
    await message.answer(welcome_text, parse_mode="HTML")

@dp.message()
async def chat_with_ai(message: types.Message):
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    try:
        chat_completion = ai_client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Sizning ismingiz 'ShavkatoV AI'. "
                        "QAT'IY QOIDA: Foydalanuvchi qaysi tilda gapirsa, faqat va faqat o'sha tilning o'zida javob bering. "
                        "Agar foydalanuvchi o'zbekcha gapirsa, unga faqat toza o'zbek tilida javob qaytaring va inglizcha tarjimalarni mutloq qo'shmang. "
                        "Agar foydalanuvchi inglizcha yozsa - faqat toza inglizcha, ruscha yozsa - faqat toza ruscha javob bering."
                    )
                },
                {
                    "role": "user",
                    "content": message.text,
                }
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
