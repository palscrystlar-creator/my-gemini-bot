import os
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web
from handlers import router # handlers.py dan router ni olamiz

BOT_TOKEN = "8799568905:AAGY-PYkbve9LkNp2Fy922FAibTopmomu5s"
WEBHOOK_URL = "https://my-gemini-bot-1-14qh.onrender.com"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
dp.include_router(router) # Router ni ulash

async def handle_webhook(request):
    data = await request.json()
    await dp.feed_update(bot, data)
    return web.Response(text="OK")

async def on_startup(app):
    await bot.set_webhook(f"{WEBHOOK_URL}/webhook")

app = web.Application()
app.router.add_post("/webhook", handle_webhook)
app.on_startup.append(on_startup)

if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
# Server qismi...
