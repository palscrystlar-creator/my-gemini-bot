import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiohttp import web
from google import genai

# Kalitlarni toʻgʻridan-toʻgʻri matn koʻrinishida yozamiz
BOT_TOKEN = "8799568905:AAGY-PYkbve9LkNp2Fy922FAibTopmomu5s"
GEMINI_API_KEY = "AQ.Ab8RN6I_DYtwmqe-rC_8o-69H_bzWhmejGFoHPb0_zYl67HYcQ"
WEBHOOK_URL = "https://my-gemini-bot-1-14qh.onrender.com"

# Server sozlamalari
PORT = int(os.environ.get("PORT", 8080))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
ai_client = genai.Client(api_key=GEMINI_API_KEY)

@dp.message(CommandStart())
async def start_command(message: types.Message):
    await message.answer(f"Salom {message.from_user.full_name}! 👋 Men VPN-siz, serverda ishlayapman!")

@dp.message()
async def chat_with_ai(message: types.Message):
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    try:
        response = ai_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=message.text,
        )
        await message.answer(response.text)
    except Exception as e:
        await message.answer("Xatolik yuz berdi.")

# Telegram'dan keladigan xabarlarni qabul qiluvchi funksiya
async def handle_webhook(request):
    url = str(request.url)
    index = url.rfind("/webhook")
    if index != -1:
        request_data = await request.json()
        update = types.Update(**request_data)
        await dp.feed_update(bot, update)
    return web.Response(text="OK")

# Server ishga tushganda webhookni o'rnatish
async def on_startup(app):
    await bot.set_webhook(f"{WEBHOOK_URL}/webhook")

def main():
    app = web.Application()
    app.router.add_post("/webhook", handle_webhook)
    app.on_startup.append(on_startup)
    web.run_app(app, host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    main()
