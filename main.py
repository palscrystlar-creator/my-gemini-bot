from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web
from handlers import router # handlers.py dan router ni ulaymiz

BOT_TOKEN = "8799568905:AAGY-PYkbve9LkNp2Fy922FAibTopmomu5s"
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Router ni dp ga ulaymiz
dp.include_router(router)

async def handle_webhook(request):
    data = await request.json()
    await dp.feed_update(bot, data)
    return web.Response(text="OK")

# Server qismi...
