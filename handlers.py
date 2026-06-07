from aiogram import Router, F, types
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from groq import Groq

router = Router()
ai_client = Groq(api_key="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")

def get_main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧮 Matematika", callback_data="start_math")],
        [InlineKeyboardButton(text="📱 Mini Ilova", callback_data="start_webapp")]
    ])

@router.message(CommandStart())
async def start_cmd(message: types.Message):
    await message.answer("Assalomu alaykum!", reply_markup=get_main_menu())

@router.message(Command("help"))
async def help_cmd(message: types.Message):
    await message.answer("Yordam: Matematika yoki suhbat.")

@router.callback_query(F.data == "start_math")
async def math_cb(callback: types.CallbackQuery):
    await callback.message.answer("Misolni yozing.")
    await callback.answer()

@router.callback_query(F.data == "start_webapp")
async def webapp_cb(callback: types.CallbackQuery):
    await callback.message.answer("Web ilovani ochish uchun tugmani bosing.")
    await callback.answer()

@router.message(F.text & ~F.text.startswith("/"))
async def chat_with_ai(message: types.Message):
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
    # AI kodi shu yerda davom etadi...
