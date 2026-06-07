import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import BotCommand
from aiohttp import web
from handlers import router # Faqat handlerlarni chaqiramiz

BOT_TOKEN = "8799568905:AAGY-PYkbve9LkNp2Fy922FAibTopmomu5s"
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
dp.include_router(router)

async def set_commands():
    await bot.set_my_commands([
        BotCommand(command="start", description="Botni ishga tushirish"),
        BotCommand(command="math", description="Matematika")
    ])

async def handle_webhook(request):
    data = await request.json()
    await dp.feed_update(bot, types.Update(**data))
    return web.Response(text="OK")

async def on_startup(app):
    await bot.set_webhook("https://my-gemini-bot-1-14qh.onrender.com/webhook")
    await set_commands()

app = web.Application()
app.router.add_post("/webhook", handle_webhook)
app.on_startup.append(on_startup)

if __name__ == "__main__":
    web.run_app(app, port=int(os.environ.get("PORT", 8080)))
